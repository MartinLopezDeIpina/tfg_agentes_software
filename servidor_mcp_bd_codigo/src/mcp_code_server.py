from dotenv import load_dotenv
load_dotenv(dotenv_path="../.env")

from utils.llm_strings_formatter import format_retrieved_chunks_into_string

import os.path
from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent
from config import REPO_ROOT_ABSOLUTE_PATH, MAX_CHUNKS, MAX_REFERENCED_CHUNKS, MAX_REFERENCING_CHUNKS
from db.db_connection import DBConnection
from db.db_utils import get_chunk_code
from mcp_tools import get_code_repository_rag_docs_from_query, get_code_from_repository_file, get_all_files_list
from utils.proyect_tree import generate_repo_tree_str

from src.pg_vector_tools import PGVectorTools

db_session = DBConnection.get_session()
mcp = FastMCP("postgre")
pgvector_tools = PGVectorTools(db_session=db_session)

def get_prueba_base_datos():
    return "query base de datos"


@mcp.tool()
async def get_code_repository_rag_docs_from_query_tool(query: str, directory: str = None) -> TextContent:
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

    json_response = get_code_repository_rag_docs_from_query(
        query=query,
        directory=directory,
        db_session=db_session,
        pgvector_tools=pgvector_tools
    )
    pretty_response = format_retrieved_chunks_into_string(json_response)
    return TextContent(
        text=pretty_response,
        type='text'
    )


@mcp.tool()
async def get_file_from_repository_tool(file_path: str) -> TextContent:
    """
    Returns all the chunks associated with a file in the repository.
    It also includes chunks that reference and are referenced by these chunks.
    :param file_path: The relative path to the file in the repository, from the repository root.
    :return: dictionary with the following structure:
        {
            "chunk_id": chunk_id,
            "chunk_content": chunk_content,
            "path": absolute path of the chunk's file,
            "referenced_chunks": list of chunks that reference this chunk
            "referencing chunks": list of chunks that are referenced by this chunk
        }
    """
    response = get_code_from_repository_file(
        file_path=file_path,
        db_session=db_session,
        pgvector_tools=pgvector_tools
    )
    pretty_response = format_retrieved_chunks_into_string(response)
    return TextContent(
        text=pretty_response,
        type='text'
    )

@mcp.tool()
async def get_repository_tree_tool(sub_path: str = None) -> TextContent:
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
    return TextContent(
        text=repo_tree_str,
        type='text'
    )

@mcp.tool()
async def get_all_respository_files_list() -> TextContent:
    """
    Devuelve una lista en formato string serializable a JSON de todos los ficheros en el repositorio respecto a su ruta relativa
    """
    files_list = get_all_files_list(db_session=db_session)
    files_list_str=str(files_list)
    return TextContent(
        text=files_list_str,
        type='text'
    )


if __name__ == "__main__":
    try:
        print("Starting MCP server...")
        mcp.run(transport='sse')

    finally:
        DBConnection.close_current_session()







