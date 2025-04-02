from src.mcp_client import MCPClient
from dotenv import load_dotenv
from src.agente_prueba import MCPAgent
from src.chunker.repo_chunker import FileChunker
from src.code_indexer.doc_generator import CodeDocGenerator

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


if __name__ == '__main__':
    load_dotenv()
    print(__package__)

    #asyncio.run(run_db_agent())
    #pruebas_repo_map()
    file_chunker = FileChunker(
        chunk_max_line_size=50,
        chunk_minimum_proportion=0.2
    )
    file_chunker.chunk_repo("/home/martin/open_source/ia-core-tools", ["alembic/versions", ".git", "/home/martin/open_source/ia-core-tools/app/model/user.py"])
    #file_chunker.chunk_repo("/home/martin/tfg_agentes_software/servidor_mcp_bd_codigo/tests/chunker/example_files")
    #file_chunker.visualize_chunks("/home/martin/open_source/ia-core-tools")
    #file_chunker.visualize_chunks_with_references("/home/martin/open_source/ia-core-tools")

    """
    docs_generator = CodeDocGenerator(
        repo_path="/home/martin/open_source/ia-core-tools",
        files_to_ignore=["alembic", ".git"]
    )
    docs_generator.create_repo_code_chunk_documentation()
    """






