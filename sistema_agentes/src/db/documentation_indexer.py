import asyncio
from os import path
from pathlib import Path
from typing import Optional, List, Any, Sequence

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel

from src.db.pgvector_utils import PGVectorStore
from config import OFFICIAL_DOCS_RELATIVE_PATH, REPO_ROOT_ABSOLUTE_PATH

class AsyncPGVectorRetriever(BaseRetriever, BaseModel):
    pg_vector_store: PGVectorStore

    class Config:
        arbitrary_types_allowed = True  # Permitir tipos no-Pydantic como PGVectorStore

    async def ainvoke(self, input: str, config: Optional[RunnableConfig] = None, **kwargs: Any) -> Sequence[Document]:
        top_k = kwargs.pop("top_k", 5)
        return await self.pg_vector_store.search_similar(query=input, top_k=top_k)

    def _get_relevant_documents(self, query, top_k):
        """
        Usar la función asíncrona
        """
        raise NotImplementedError

class AsyncDocsIndexer:
    pg_vector_store: PGVectorStore

    def __init__(self, collection_name: str):
        self.pg_vector_store = PGVectorStore(collection_name=collection_name)


    async def index_file(self, file_path: Path) -> None:
        docs_absolute_path = f"{REPO_ROOT_ABSOLUTE_PATH}{OFFICIAL_DOCS_RELATIVE_PATH}"
        metadata = {
            "file_path": str(file_path.relative_to(docs_absolute_path))
        }

        await self.pg_vector_store.index_resource(resource=file_path, metadata=metadata)


    async def index_all_directory_files(self, directory_path: str) -> None:
        base_dir = Path(directory_path).absolute()

        all_files = list(base_dir.rglob('*'))
        file_paths = [f for f in all_files if f.is_file()]
        total_files = len(file_paths)
        print(f"Found {total_files} files to process in {directory_path}")

        tasks = [self.index_file(file_path) for file_path in file_paths]

        await asyncio.gather(*tasks)

    async def index_all_directory_files_if_not_indexed(self, directory_path: str):
        is_collection_empty =  await self.pg_vector_store.is_collection_empty()
        if not is_collection_empty:
            print(f"Documentación previamente indexada")
            return

        await self.index_all_directory_files(directory_path)

    def get_retriever(self) -> AsyncPGVectorRetriever:
        return AsyncPGVectorRetriever(
            pg_vector_store=self.pg_vector_store
        )

