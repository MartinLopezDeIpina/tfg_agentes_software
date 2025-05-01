from typing import Sequence

from langchain_core.retrievers import BaseRetriever
from langchain_core.tools import BaseTool, tool

from config import REPO_ROOT_ABSOLUTE_PATH, OFFICIAL_DOCS_RELATIVE_PATH
from src.db.documentation_indexer import AsyncPGVectorRetriever
from src.mcp_client.tool_wrapper import patch_tool_with_exception_handling
from src.utils import tab_all_lines_x_times
from src.db.documentation_indexer import AsyncDocsIndexer
from config import REPO_ROOT_ABSOLUTE_PATH, OFFICIAL_DOCS_RELATIVE_PATH


def get_docs_rag_tool(langchain_retriever: AsyncPGVectorRetriever) -> BaseTool:

    @tool
    async def rag_search_documentation(query: str):
        """
        Perform a relevant documents search for the provided query.
        Useful when it is not clear which document to read.

        Args:
            query: query for which to search relevant documents
        Returns:
            relevant documents from the official documentation
        """
        relevant_documents = await langchain_retriever.ainvoke(input=query, top_k=15)

        tool_result = ""
        for document in relevant_documents:
            tool_result += f"Chunk in {document.metadata["file_path"]}:\n"
            tool_result += tab_all_lines_x_times(document.page_content)
            tool_result += "\n"

        return tool_result
    
    return rag_search_documentation


async def get_file_system_agent_additional_tools() -> Sequence[BaseTool]:
    collection_name="official_documentation"
    documentation_path = f"{REPO_ROOT_ABSOLUTE_PATH}{OFFICIAL_DOCS_RELATIVE_PATH}"

    documents_indexer = AsyncDocsIndexer(collection_name=collection_name)
    await documents_indexer.index_all_directory_files_if_not_indexed(directory_path=documentation_path)
    retriever = documents_indexer.get_retriever()

    rag_tool = get_docs_rag_tool(langchain_retriever=retriever)
    tools = [
        rag_tool
    ]
    wrapped_tools = [patch_tool_with_exception_handling(tool) for tool in tools]
    return wrapped_tools
