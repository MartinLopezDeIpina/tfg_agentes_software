import asyncio
from pathlib import Path
from typing import Sequence, List

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
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from config import PGVECTOR_COLLECTION_PREFIX, default_embedding_llm
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

async def save_agent_memory_in_store(store: AsyncPostgresStore, values: dict, agent_name: str, key:str):
    await store.aput(
        namespace=("documents", agent_name),
        key=key,
        value=values
    )

async def increment_counter(store: AsyncPostgresStore, item: SearchItem):
    if "access_count" in item.value:
        item.value["access_count"] += 1

    try:
        await save_agent_memory_in_store(
            store=store,
            values=item.value,
            agent_name=item.namespace[1],
            key=item.key
        )
    except Exception as e:
        print(f"Error guardando memoria en store: {e}")

async def increment_memory_docs_counter(store: AsyncPostgresStore, memory_docs: List[SearchItem]):
    tasks = [increment_counter(store=store, item=item) for item in memory_docs]
    await asyncio.gather(*tasks)

async def hybrid_memory_similarity_counter_search(store: AsyncPostgresStore, agent_name: str, query: str, k_docs: int = 5, similarity_weight: float = 0.75, counter_weight: float = 0.25):
    memory_docs = await store.asearch(("documents", agent_name), query=query, limit=k_docs * 2)
    if not memory_docs:
        return []

    # Normalizar los contadores en una escala del 0-1
    max_counter = max([doc.value.get("access_count", 0) for doc in memory_docs], default=1)

    # Crear una lista de tuplas (documento, score_híbrido)
    scored_docs = []
    for doc in memory_docs:
        similarity_score = doc.score or 0

        access_counter = doc.value.get("access_count", 0)
        normalized_counter = access_counter / max_counter if max_counter > 0 else 0

        hybrid_score = (
                similarity_weight * similarity_score +
                counter_weight * normalized_counter
        )

        scored_docs.append((doc, hybrid_score))

    scored_docs.sort(key=lambda x: x[1], reverse=True)

    return [doc for doc, _ in scored_docs[:k_docs]]

async def delete_all_memory_documents(store: AsyncPostgresStore):
    deleted_count = 0

    namespaces = await store.alist_namespaces()

    # Para cada namespace, buscar todos los elementos y eliminarlos
    for namespace in namespaces:
        items = await store.asearch(namespace)

        # Eliminar cada elemento encontrado
        delete_ops = []
        for item in items:
            # Crear una operación de eliminación para cada documento
            delete_ops.append(PutOp(namespace=item.namespace, key=item.key, value=None))
            deleted_count += 1

        # Ejecutar las operaciones de eliminación en batch si hay elementos
        if delete_ops:
            await store.abatch(delete_ops)

    print(f"Se han eliminado {deleted_count} documentos")
    return deleted_count




