from config import files_to_ignore, DIRECTROY_TO_INDEX
from dotenv import load_dotenv

from db.db_connection import DBConnection

load_dotenv()

from src.code_indexer.repo_async_pipeline import run_documentation_pipeline_sync
from src.chunker.repo_chunker import FileChunker

if __name__ == '__main__':
    try:
        print(__package__)

        file_chunker = FileChunker(
            chunk_max_line_size=200,
            chunk_minimum_proportion=0.2
        )

        """
        file_chunker.chunk_repo("/home/martin/open_source/ia-core-tools",
                                [".git",
                                 "app/static/css/style.css",
                                 "app/static/js/bootstrap.bundle.js",
                                 "app/static/js/bootstrap.bundle.min.js",
                                 "app/static/vendor"]
                                )
        """
        #file_chunker.chunk_repo(DIRECTROY_TO_INDEX)

        #file_chunker.visualize_chunks("/home/martin/open_source/ia-core-tools")
        #file_chunker.visualize_chunks_with_references("/home/martin/open_source/ia-core-tools")

        run_documentation_pipeline_sync(DIRECTROY_TO_INDEX, files_to_ignore)

        """
        docs_generator = CodeDocGenerator(
            repo_path="/home/martin/open_source/ia-core-tools",
            files_to_ignore=["alembic", ".git"]
        )
        docs_generator.create_repo_code_chunk_documentation_asynchronously()
        """

        #asyncio.run(get_code_repository_rag_docs_from_query_tool(query="Herramientas de IA para agentes LLM"))
        """
        asyncio.run(get_file_from_repository_tool(file_path="app/tools/modelTool.py"))
        """

    finally:
        DBConnection.close_current_session()







