from dotenv import load_dotenv

from db.db_connection import DBConnection

load_dotenv()

import asyncio

from code_indexer.llm_tools import AsyncEmbedder
from mcp_code_server import get_code_repository_rag_docs_from_query_tool, get_file_from_repository_tool
from src.code_indexer.repo_async_pipeline import run_documentation_pipeline_sync
from src.mcp_client import MCPClient
from src.agente_prueba import MCPAgent
from src.chunker.repo_chunker import FileChunker

async def run_db_agent():
    mcp_client = MCPClient()
    try:
        await mcp_client.connect_to_server()

        tools = mcp_client.get_tools()
        mcp_agent = MCPAgent(tools)
        resultado = mcp_agent.ejecutar_agente()
        print(f"resultado: {resultado}")
    finally:
        await mcp_client.cleanup()

async def prueba():
    embedder = AsyncEmbedder()
    texto_ejemplo = "hola"
    resultado = await embedder.async_embed_document(texto_ejemplo)
    print("debug")

if __name__ == '__main__':
    print(__package__)

    #asyncio.run(run_db_agent())
    #pruebas_repo_map()
    file_chunker = FileChunker(
        chunk_max_line_size=250,
        chunk_minimum_proportion=0.2
    )
    files_to_ignore = [".git",
     "app/static/css/style.css",
     "app/static/js/bootstrap.bundle.js",
     "app/static/js/bootstrap.bundle.min.js",
     "app/static/vendor"]

    """
    file_chunker.chunk_repo("/home/martin/open_source/ia-core-tools",
                            [".git",
                             "app/static/css/style.css",
                             "app/static/js/bootstrap.bundle.js",
                             "app/static/js/bootstrap.bundle.min.js",
                             "app/static/vendor"]
                            )
    """
    #file_chunker.chunk_repo("/home/martin/tfg_agentes_software/servidor_mcp_bd_codigo/tests/chunker/example_files")

    #file_chunker.visualize_chunks("/home/martin/open_source/ia-core-tools")
    #file_chunker.visualize_chunks_with_references("/home/martin/open_source/ia-core-tools")

    run_documentation_pipeline_sync("/home/martin/open_source/ia-core-tools", files_to_ignore)

    """
    docs_generator = CodeDocGenerator(
        repo_path="/home/martin/open_source/ia-core-tools",
        files_to_ignore=["alembic", ".git"]
    )
    docs_generator.create_repo_code_chunk_documentation_asynchronously()
    """
    #asyncio.run(prueba())


    #asyncio.run(get_code_repository_rag_docs_from_query_tool(query="Herramientas de IA para agentes LLM"))
    """
    asyncio.run(get_file_from_repository_tool(file_path="app/tools/modelTool.py"))
    """

    DBConnection.close_current_session()







