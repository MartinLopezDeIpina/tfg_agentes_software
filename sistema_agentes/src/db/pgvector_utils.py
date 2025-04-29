from pathlib import Path
from typing import Sequence

from langchain_community.document_loaders import PyPDFLoader, TextLoader, CSVLoader, UnstructuredFileLoader
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_postgres import PGVector
from langchain_text_splitters import CharacterTextSplitter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from config import PGVECTOR_COLLECTION_PREFIX, default_embedding_llm
from src.db.postgres_connection_manager import PostgresPoolManager

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
        elif ext == '.txt' or ext == '.md':
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
        Indexa un documento utilizando un laoder para generar los chunks
        Añade los metadatos indicados
        """
        if not metadata:
            metadata = {}

        loader = self._get_loader_for_file(resource)

        pages = loader.load()
        text_splitter = CharacterTextSplitter(chunk_size=150, chunk_overlap=10)
        docs = text_splitter.split_documents(pages)

        for doc in docs:
            doc.metadata = metadata

        result = await self.vector_store.aadd_documents(docs)
        print(result)


    async def is_collection_empty(self) -> bool:
        collection_name = self.vector_store.collection_name
        sql = text(f"SELECT COUNT(*) FROM {collection_name}")

        async with self.engine.connect() as connection:
            result = await connection.execute(sql)
            row = result.fetchone()
            count = row[0] if row else 0
            return count == 0

    async def search_similar(self, query: str, top_k: int = 5) -> Sequence[Document]:
        """
        Busca documentos similares en la colección usando la query y similitud coseno
        """
        results = await self.vector_store.asimilarity_search(query, k=top_k)
        return results

