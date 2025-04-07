from config import REPO_ROOT_ABSOLUTE_PATH, MAX_CHUNKS, MAX_REFERENCED_CHUNKS, MAX_REFERENCING_CHUNKS
from db.db_utils import get_chunk_code
from src.pg_vector_tools import PGVectorTools
from sqlalchemy.orm import Session


def get_code_repository_rag_docs_from_query(db_session: Session, pgvector_tools: PGVectorTools, query: str, directory: str = None) -> dict:
    top_similar_chunks = pgvector_tools.search_similar_chunks(
        directory_path=directory,
        query=query,
        max_results=MAX_CHUNKS
    )

    response = process_chunks_referenced_and_referencing(top_similar_chunks, db_session)
    return response

def process_chunks_referenced_and_referencing(chunks, db_session, max_chunks=MAX_CHUNKS,
                                              max_referenced=MAX_REFERENCED_CHUNKS,
                                              max_referencing=MAX_REFERENCING_CHUNKS):
    """
    Procesa los chunks y recopila sus chunks referenciados y referenciantes.
    """
    included_chunk_ids = set()
    response = {}

    for chunk in chunks:
        if len(included_chunk_ids) >= max_chunks:
            break

        chunk_id = chunk.chunk_id
        if chunk_id not in included_chunk_ids:
            included_chunk_ids.add(chunk_id)
            process_chunk(chunk, included_chunk_ids, response, db_session,
                         max_referenced, max_referencing)

    return response

def process_chunk(chunk, included_chunk_ids, response, db_session,
                 max_referenced, max_referencing):
    """
    Procesa un chunk individual y sus relaciones.
    """
    chunk_id = chunk.chunk_id

    # Procesar chunks referenciados
    referenced_chunks_dict = process_related_chunks(
        chunk.referenced_chunks, included_chunk_ids, db_session, max_referenced)

    # Procesar chunks referenciantes
    referencing_chunks_dict = process_related_chunks(
        chunk.referencing_chunks, included_chunk_ids, db_session, max_referencing)

    # Agregar los datos del chunk principal
    response[chunk_id] = {
        **add_chunk_to_dict(chunk, db_session),
        "referenced_chunks": referenced_chunks_dict,
        "referencing_chunks": referencing_chunks_dict
    }

def process_related_chunks(related_chunks, included_chunk_ids, db_session, max_chunks):
    """
    Procesa chunks relacionados (referenciados o referenciantes) hasta un máximo especificado.
    """
    result_dict = {}
    count = 0

    for related_chunk in related_chunks:
        if count >= max_chunks:
            break

        count += 1
        related_chunk_id = related_chunk.chunk_id

        if related_chunk_id not in included_chunk_ids:
            included_chunk_ids.add(related_chunk_id)
            result_dict[related_chunk_id] = add_chunk_to_dict(related_chunk, db_session)

    return result_dict

def add_chunk_to_dict(chunk, db_session):
    """
    Crea un diccionario con el contenido y la ruta de un chunk dado.
    """
    return {
        "path": chunk.file.path,
        "chunk_content": get_chunk_code(db_session, chunk)
    }

def get_code_from_repository_file(db_session: Session, pgvector_tools: PGVectorTools, file_path: str) -> dict:
    chunks = pgvector_tools.get_file_chunks(file_path)

    response = process_chunks_referenced_and_referencing(
        chunks=chunks,
        db_session=db_session
    )
    return response








