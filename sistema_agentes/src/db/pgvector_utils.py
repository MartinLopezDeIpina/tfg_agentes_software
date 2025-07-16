import asyncio
from collections import defaultdict
from pathlib import Path
from typing import Sequence, List

import numpy as np
from langchain_community.document_loaders import PyPDFLoader, TextLoader, CSVLoader, UnstructuredFileLoader
from langchain_community.vectorstores.pgembedding import CollectionStore
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.stores import BaseStore
from langchain_postgres import PGVector
from langchain_text_splitters import CharacterTextSplitter, ExperimentalMarkdownSyntaxTextSplitter
from langgraph.store.base import PutOp
from langgraph.store.postgres import AsyncPostgresStore
from langgraph_sdk.schema import SearchItem
from matplotlib import pyplot as plt
from sklearn.cluster import KMeans
from sklearn.manifold import TSNE
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from config import PGVECTOR_COLLECTION_PREFIX, default_embedding_llm, STORE_COLLECTION_PREFIX
from src.db.postgres_connection_manager import PostgresPoolManager
from src.utils import read_file_content


class PGVectorStore:
    vector_store: PGVector
    engine: AsyncEngine
    embeddings: Embeddings

    def __init__(self, collection_name: str, async_engine: AsyncEngine = None, embeddings: Embeddings = None):
        if hasattr(self, "_initialized") and self._initialized:
            return

        if embeddings is None:
            embeddings = default_embedding_llm
        if async_engine is None:
            async_engine = PostgresPoolManager.get_engine()

        self.engine = async_engine
        self.embeddings = embeddings
        self.vector_store = self.create_async_vector_store(collection_name)

    def create_async_vector_store(self, collection_name: str) -> PGVector:
        prefixed_name = PGVECTOR_COLLECTION_PREFIX + collection_name
        # Crear o cambiar a una nueva colección
        vector_store = PGVector(
            embeddings=self.embeddings,
            collection_name=prefixed_name,
            connection=self.engine,
            use_jsonb=True,
            async_mode=True
        )
        return vector_store

    def _get_loader_for_file(self, file_path: Path):
        """Devuelve el file loader apropiado basado en el tipo de documento"""
        ext = file_path.suffix.lower()
        if ext == '.pdf':
            return PyPDFLoader(str(file_path), extract_images=False)
        elif ext == '.md':
            return ExperimentalMarkdownSyntaxTextSplitter
        elif ext == '.txt':
            return TextLoader(str(file_path))
        elif ext in ['.csv', '.tsv']:
            return CSVLoader(str(file_path))
        else:
            try:
                return UnstructuredFileLoader(str(file_path))
            except:
                return None

    async def index_resource(self, resource: Path, metadata: dict = None):
        """
        Indexa los documentos separandolos en chunks según los títulos markdown
        """
        if not metadata:
            metadata = {}

        resource_text = read_file_content(resource)

        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
        ]

        splitter = ExperimentalMarkdownSyntaxTextSplitter(
            headers_to_split_on=headers_to_split_on,
            strip_headers=False
        )
        docs = splitter.split_text(resource_text)

        for doc in docs:
            doc.metadata = metadata

        await self.vector_store.aadd_documents(docs)
        print(f"Added document: {resource.absolute()}")


    async def is_collection_empty(self) -> bool:
        await self.create()
        async with AsyncSession(self.engine) as session:
            collection = await session.execute(
                select(CollectionStore).where(CollectionStore.name == self.vector_store.collection_name)
            )
            collection_instance = collection.scalar_one_or_none()
            if not collection_instance:
                return True
            return False

    async def create(self):
        await self.vector_store.acreate_collection()

    async def delete_collection(self):
        await self.vector_store.adelete_collection()

    async def search_similar(self, query: str, top_k: int = 5) -> Sequence[Document]:
        """
        Busca documentos similares en la colección usando la query y similitud coseno
        """
        results = await self.vector_store.asimilarity_search(query, k=top_k)
        return results

