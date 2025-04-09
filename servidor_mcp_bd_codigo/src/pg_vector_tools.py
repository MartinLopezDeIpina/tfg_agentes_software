from typing import List

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_postgres.vectorstores import PGVector
from langchain_core.embeddings.embeddings import Embeddings
from config import EMBEDDER_MODEL_INSTANCE
from db.db_utils import get_fs_entry_from_relative_path, get_root_fs_entry, get_chunk_code
from db.models import FileChunk, Ancestor, FSEntry
from src.db.db_connection import DBConnection
from sqlalchemy import select
from sqlalchemy.sql import func



class PGVectorTools:
    def __init__(self, embedder_instance: Embeddings = EMBEDDER_MODEL_INSTANCE, db_session=None):
        self.db_session = db_session or DBConnection.get_session()
        self.embedder_instance = embedder_instance

    def search_similar_chunks(self, query: str, directory_path: str = None, max_results: int = 10) -> List[FileChunk]:
        query_embedding = self.embedder_instance.embed_query(query)

        # Si no se proporciona un directorio o no se encuentra, se busca desde el directorio raíz
        fs_entry = None
        if directory_path:
            fs_entry = get_fs_entry_from_relative_path(self.db_session, directory_path)
        if directory_path is None or fs_entry is None:
            fs_entry = get_root_fs_entry(self.db_session)

        # Filtrar primero los descendientes con la closure table
        descendant_ids = select(Ancestor.descendant_id).where(
            Ancestor.ancestor_id == fs_entry.id
        ).scalar_subquery()

        # Buscar los chunks por orden de similitud haciendo un join con la tabla de fsentry
        stmt = select(FileChunk, FileChunk.embedding.cosine_distance(query_embedding).label('distance'))\
            .join(FSEntry, FSEntry.id == FileChunk.file_id)\
            .where(FileChunk.file_id.in_(descendant_ids))\
            .order_by('distance')\
            .limit(max_results)

        results = self.db_session.execute(stmt).all()

        similar_chunks = [result[0] for result in results]

        return similar_chunks

    def get_file_chunks(self, file_path: str) -> List[FileChunk]:
        """
        Obtiene todos los chunks de un archivo específico.
        :param file_path: Ruta relativa al archivo dentro del repositorio.
        :return: Lista de objetos FileChunk.
        """
        fs_entry = get_fs_entry_from_relative_path(self.db_session, file_path)
        if fs_entry is None:
            raise FileNotFoundError(f"File not found: {file_path}")

        stmt = select(FileChunk).where(FileChunk.file_id == fs_entry.id)
        results = self.db_session.execute(stmt).scalars().all()
        return results



