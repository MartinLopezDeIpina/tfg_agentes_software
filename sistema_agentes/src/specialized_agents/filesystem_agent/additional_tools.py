from typing import Sequence

from langchain_core.retrievers import BaseRetriever
from langchain_core.tools import BaseTool, tool

from config import REPO_ROOT_ABSOLUTE_PATH, OFICIAL_DOCS_RELATIVE_PATH
from src.db.documentation_indexer import AsyncPGVectorRetriever, AsyncDirectoryIndexer
from src.mcp_client.tool_wrapper import patch_tool_with_exception_handling
from src.utils import tab_all_lines_x_times


def get_docs_rag_tool(langchain_retriever: AsyncPGVectorRetriever) -> BaseTool:

    @tool
    async def rag_search_documentation(query: str):
        """
        Perform a relevant documents search for the provided query.

        Args:
            query: query for which to search relevant documents
        Returns:
            relevant documents from the official documentation
        """
        relevant_documents = await langchain_retriever._aget_relevant_documents(query=query)

        tool_result = ""
        for document in relevant_documents:
            tool_result += f"Chunk in {document.metadata["file_path"]}:\n"
            tool_result += tab_all_lines_x_times(document.page_content)
            tool_result += "\n"

        return tool_result
    
    return rag_search_documentation

async def get_file_system_agent_additional_tools() -> Sequence[BaseTool]:
    documents_indexer = await AsyncDirectoryIndexer.create()
    documentation_path = f"{REPO_ROOT_ABSOLUTE_PATH}{OFICIAL_DOCS_RELATIVE_PATH}"

    collection_name="official_documentation"
    await documents_indexer.index_all_directory_files_if_not_indexed(
        directory_path=documentation_path,
        collection_name=collection_name
    )

    documents_retriever = AsyncPGVectorRetriever(
        indexer=documents_indexer,
        collection_name=collection_name
    )

    rag_tool = get_docs_rag_tool(documents_retriever)
    tools = [
        rag_tool
    ]
    wrapped_tools = [patch_tool_with_exception_handling(tool) for tool in tools]
    return wrapped_tools
