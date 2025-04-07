import os.path

from mcp.server.fastmcp import FastMCP
from config import REPO_ROOT_ABSOLUTE_PATH, MAX_CHUNKS, MAX_REFERENCED_CHUNKS, MAX_REFERENCING_CHUNKS
from db.db_connection import DBConnection
from db.db_utils import get_chunk_code
from mcp_tools import get_code_repository_rag_docs_from_query
from utils.proyect_tree import generate_repo_tree_str

from src.pg_vector_tools import PGVectorTools

db_session = DBConnection.get_session()
mcp = FastMCP("postgre")
pgvector_tools = PGVectorTools(db_session=db_session)

def get_prueba_base_datos():
    return "query base de datos"


@mcp.tool()
async def get_code_repository_rag_docs_from_query_tool(query: str, directory: str = None) -> dict:
    """
    Returns chunks of code from the repository subdirectory that are similar or relevant to the provided query.

    :param query: The query to search for in the code repository.
    :param directory: Subdirectory where to perform the search. The search runs recursively,
                 including all files in this directory and at any level of subdirectories
                 within it. If None, the repository root directory will be used.
    :return: dictionary with the following structure:
        {
            "chunk_id": chunk_id,
            "chunk_content": chunk_content,
            "path": absolute path of the chunk's file,
            "referenced_chunks": list of chunks that reference this chunk
            "referencing chunks": list of chunks that are referenced by this chunk
        }
    """

    response = get_code_repository_rag_docs_from_query(
        query=query,
        directory=directory,
        db_session=db_session,
        pgvector_tools=pgvector_tools
    )
    return response



@mcp.tool()
async def get_file_from_repository(file_path: str) -> str:
    """
    Returns the content of a file in the repository.
    :param file_path: The relative path to the file in the repository, from the repository root.
    :return: string with the content of the file.
    """
    pass



    similar_resources = pgvector_tools.search_similar_resources(query, 5)

    return similar_resources

#todo: se podría hacer que este devuelva el tree con detalles de las definiciones -> no es necesario
@mcp.tool()
async def get_repository_tree(sub_path: str = None) -> str:
    """
    Returns a tree of the files and directories in the repository.
    :param sub_path:
        The sub-path directory to list, relative to the repository root.
        If not indicated, the root directory is listed.
    :return: String representation of the tree.
    """

    if sub_path is None:
        sub_path = REPO_ROOT_ABSOLUTE_PATH
    else:
        sub_path = os.path.join(REPO_ROOT_ABSOLUTE_PATH, sub_path)

    repo_tree_str = generate_repo_tree_str(sub_path)

    return repo_tree_str


if __name__ == "__main__":

    mcp.run(transport='sse')







