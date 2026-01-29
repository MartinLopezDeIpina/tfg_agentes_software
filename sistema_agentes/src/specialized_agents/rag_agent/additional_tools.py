from datetime import datetime
from typing import Sequence

from langchain_core.retrievers import BaseRetriever
from langchain_core.tools import BaseTool, tool

from config import REPO_ROOT_ABSOLUTE_PATH, OFFICIAL_DOCS_RELATIVE_PATH, GITLAB_MOCK_ISSUES, GITLAB_MOCK_COMMITS, \
    GITLAB_MOCK_MEMBERS
from src.db.documentation_indexer import AsyncPGVectorRetriever
from src.mcp_client.tool_wrapper import patch_tool_with_exception_handling
from src.utils import tab_all_lines_x_times
from src.db.documentation_indexer import AsyncDocsIndexer
from config import REPO_ROOT_ABSOLUTE_PATH, OFFICIAL_DOCS_RELATIVE_PATH


def get_rag_general_doc_tool(langchain_retriever: AsyncPGVectorRetriever) -> BaseTool:
    @tool
    async def rag_search_general_documentation(query: str):
        """
        Perform a relevant documents search for the provided query in the general documentation.
        General documentation contains project management, software architecture, code standards, methodology and onboarding information.

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

    return rag_search_general_documentation

def get_rag_visual_docs_tool(langchain_retriever: AsyncPGVectorRetriever) -> BaseTool:
    @tool
    async def rag_search_visual_documentation(query: str):
        """
        Perform a relevant documents search for the provided query in the frontend / visual documentation.

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

    return rag_search_visual_documentation

def get_rag_mock_templates_tool(langchain_retriever: AsyncPGVectorRetriever) -> BaseTool:
    @tool
    async def rag_search_mock_templates(query: str):
        """
        Perform a relevant documents search for the provided query in the HTML mock templates of the project 
        """
        relevant_documents = await langchain_retriever.ainvoke(input=query, top_k=15)

        tool_result = ""
        for document in relevant_documents:
            tool_result += f"Chunk in {document.metadata["file_path"]}:\n"
            tool_result += tab_all_lines_x_times(document.page_content)
            tool_result += "\n"

        return tool_result

    return rag_search_mock_templates


import json
from typing import List, Optional


@tool
def get_gitlab_issues(issue_ids: List[int] = None, filepath: str = GITLAB_MOCK_ISSUES):
    """
    Get the issues from the GitLab repository.
    If not issue_ids are provided, it will return all issues.

    Args:
        issue_ids (List[int]): List of issue IDs to retrieve.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # If no specific issue_ids requested, return everything
    if issue_ids is None or len(issue_ids) == 0:
        return data

    filtered_issues = [
        issue for issue in data["issues"]
        if issue["iid"] in issue_ids
    ]
    filtered_summary = {
        "total_count": len(filtered_issues),
        "open_count": sum(1 for issue in filtered_issues if issue["state"] == "opened"),
        "closed_count": sum(1 for issue in filtered_issues if issue["state"] == "closed"),
        "labels": list(set(
            label
            for issue in filtered_issues
            for label in issue.get("labels", [])
        ))
    }
    return {
        "summary": filtered_summary,
        "issues": filtered_issues
    }


@tool
def get_gitlab_project_commits(
        user_name: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        result_limit: int = 25,
        filepath: str = GITLAB_MOCK_COMMITS
):
    """
     Get the commit information of the GitLab repository.

     If no user name is provided, it will return the commits of all users.
     If no dates are provided, it will return the commits of all time.

     Results will be limited to the most recent 25 commits.

     Args:
         user name (str): The name of the user account. It must be the same as the one used in GitLab.
         since (datetime): The date to start retrieving commits from.
         until (datetime): The date to stop retrieving commits from.
         result_limit (int): The number of maximum commits to show, should be 25 unless exceptional cases.
     """

    with open(filepath, 'r', encoding='utf-8') as f:
        commits = json.load(f)

    filtered_commits = []

    for commit in commits:
        if user_name and commit.get("author") != user_name:
            continue
        commit_date_str = commit.get("date", "")
        try:
            commit_date = datetime.strptime(commit_date_str, "%Y-%m-%d %H:%M:%S %z")
        except ValueError:
            if since or until:
                continue
            commit_date = None
        if since and commit_date:
            if commit_date < since:
                continue
        if until and commit_date:
            if commit_date > until:
                continue
        filtered_commits.append(commit)

        if len(filtered_commits) >= result_limit:
            break

    return filtered_commits


@tool
def get_gitlab_project_members(filepath: str = GITLAB_MOCK_MEMBERS):
    """
    Get the project's member information.
    This includes the user name, id and role among others.
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)



async def get_rag_agent_additional_tools() -> Sequence[BaseTool]:
    #collection_names = ["general_docs_rag", "visual_docs_rag", "mocks_docs_rag"]

    retriever_general_docs = AsyncDocsIndexer(collection_name="general_docs_rag").get_retriever()
    tool_general_docs = get_rag_general_doc_tool(retriever_general_docs)
    retriever_visual_docs = AsyncDocsIndexer(collection_name="visual_docs_rag").get_retriever()
    tool_visual_docs = get_rag_visual_docs_tool(retriever_visual_docs)
    retriever_mocks_docs = AsyncDocsIndexer(collection_name="mocks_docs_rag").get_retriever()
    tool_mocks_docs = get_rag_mock_templates_tool(retriever_mocks_docs)

    wrapped_tools = [patch_tool_with_exception_handling(tool) for tool in
                     [tool_general_docs,
                      tool_visual_docs,
                      tool_mocks_docs,
                      get_gitlab_project_members,
                      get_gitlab_project_commits,
                      get_gitlab_issues]
                     ]
    return wrapped_tools