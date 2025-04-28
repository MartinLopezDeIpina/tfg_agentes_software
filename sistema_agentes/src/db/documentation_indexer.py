from pathlib import Path
from typing import Sequence

from langchain_text_splitters import CharacterTextSplitter
from sqlalchemy import text

from langchain_community.document_loaders import PyPDFLoader, TextLoader, CSVLoader, UnstructuredFileLoader
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector

from config import default_embedding_llm, psycopg_connection_string
from src.db.postgres_connection_manager import PostgresPoolManager

COLLECTION_PREFIX = "collection_"

class AsyncDirectoryIndexer:
    def __init__(self,engine,  embeddings_model: OpenAIEmbeddings, chunk_size: int, chunk_overlap: int):
        """
        Args:
            embeddings_model: LangChain embedding model to use
            chunk_size: Number of lines per chunk
            chunk_overlap: Number of lines to overlap per chunk
        """
        self.engine = engine
        self.embeddings = embeddings_model or OpenAIEmbeddings()
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.vector_store = None
        self.current_collection_name = None

    @classmethod
    async def create(cls, embeddings_model: OpenAIEmbeddings = None,
                     chunk_size: int = 10, chunk_overlap: int = 2):
        if embeddings_model is None:
            embeddings_model = default_embedding_llm

        engine = PostgresPoolManager.get_engine()

        return cls(engine, embeddings_model, chunk_size, chunk_overlap)

    def create_vector_store(self, collection_name: str):
        prefixed_name = COLLECTION_PREFIX + collection_name
        # Crear o cambiar a una nueva colección
        self.vector_store = PGVector(
            embeddings=self.embeddings,
            collection_name=prefixed_name,
            connection=self.engine,
            use_jsonb=True,
            async_mode=True
        )
        self.current_collection_name = prefixed_name
        return self.vector_store

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

    async def process_file(self, file_path: Path, base_dir: Path):

        loader = self._get_loader_for_file(file_path)
        if not loader:
            print(f"No se encontró loader para tipo de fichero: {file_path}")
            return

        try:
            documents = await loader.aload()
            rel_path = str(file_path.relative_to(base_dir))
            text_splitter = CharacterTextSplitter(chunk_size=150, chunk_overlap=10)
            docs = text_splitter.split_documents(documents)

            for doc in docs:
                doc.metadata["file_path"] = rel_path

            await self.vector_store.aadd_documents(docs)
            print(f"Indexed {len(docs)} chunks from {rel_path}")

        except Exception as e:
            print(f"Error processing file {file_path}: {e}")

    async def is_collection_empty(self) -> bool:
        table_name = self.current_collection_name
        sql = text(f"SELECT COUNT(*) FROM {table_name}")

        async with self.engine.connect() as connection:
            result = await connection.execute(sql)
            row = result.fetchone()
            count = row[0] if row else 0
            return count == 0

    async def index_all_directory_files_if_not_indexed(self, directory_path: str, collection_name: str):
        self.create_vector_store(collection_name)

        is_collection_empty =  await self.is_collection_empty()
        if not is_collection_empty:
            print(f"Documentación previamente indexada")
            return

        base_dir = Path(directory_path).absolute()

        all_files = list(base_dir.rglob('*'))
        file_paths = [f for f in all_files if f.is_file()]
        total_files = len(file_paths)
        print(f"Found {total_files} files to process in {directory_path}")

        # Process files in batches for better progress reporting
        processed = 0
        batch_size = 10
        for i in range(0, len(file_paths), batch_size):
            # Get current batch
            batch = file_paths[i:i + batch_size]
            batch_number = i // batch_size + 1
            total_batches = (len(file_paths) - 1) // batch_size + 1

            print(f"Processing batch {batch_number}/{total_batches}...")
            batch_processed = 0
            for file_path in batch:
                try:
                    await self.process_file(file_path, base_dir)
                    batch_processed += 1
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
            processed += batch_processed
            print(f"Batch {batch_number}/{total_batches} completed. Progress: {processed}/{total_files} files")

        print(f"Indexing complete. Processed {processed} files.")

    async def search_similar(self, query: str, collection_name: str, top_k: int = 5) -> Sequence[Document]:
        """
        Busca documentos similares en la colección usando la query y similitud coseno
        """
        results = await self.vector_store.asimilarity_search(query, k=top_k)
        return results

class AsyncPGVectorRetriever(BaseRetriever):
    def __init__(self, indexer: AsyncDirectoryIndexer, collection_name: str):
        super().__init__()
        self.indexer = indexer
        self.collection_name = collection_name

    async def _aget_relevant_documents(self, query, *, run_manager=None):
        return await self.indexer.search_similar(query, self.collection_name)

    def _get_relevant_documents(self, query, *, run_manager=None):
        """
        Usar la función asíncrona
        """
        raise NotImplementedError