import os
from datetime import datetime
from typing import Dict, Any, List, Optional

import mcp
import requests
from langchain_core.tools import BaseTool, tool

from src.mcp_client.tool_wrapper import patch_tool_with_exception_handling


@tool
def get_gitlab_issues(issue_ids: List[int] = None):
    """
    Get the issues from the GitLab repository.
    If not issue_ids are provided, it will return all issues.

    Args:
        issue_ids (List[int]): List of issue IDs to retrieve.
    """
    if issue_ids is None:
        issue_ids = []


    if len(issue_ids) == 0:
        url = f"issues"
    else:
        iids_params = "&".join([f"iids[]={issue_id}" for issue_id in issue_ids])
        url = f"issues?{iids_params}"

    issues = execute_gitlab_api_request(url)
    return issues

@tool
def get_gitlab_project_statistics():
    """
    Get the statistics of the GitLab project, including the number of issues, merge requests, and users.
    """
    url =""
    result = execute_gitlab_api_request(url)
    return result

@tool
def get_gitlab_project_members():
    """
    Get the project's member information.
    This includes the user name, email, and role of each member.
    """
    url = "members"
    result = execute_gitlab_api_request(url)
    return result

@tool
def get_gitlab_braches():
    """
    Get the available branches of the GitLab repository.
    """
    url = "repository/branches"
    branches = execute_gitlab_api_request(url)
    return branches

@tool
def get_gitlab_project_commits(user_name: Optional[str] = None, since: Optional[datetime] = None, until: Optional[datetime] = None):
    """
    Get the commit information of the GitLab repository.

    If no user name is provided, it will return the commits of all users.
    If no dates are provided, it will return the commits of all time.

    Results will be limited to the most recent 25 commits.

    Args:
        user name (str): The name of the user account. It must be the same as the one used in GitLab.
        since (datetime): The date to start retrieving commits from.
        until (datetime): The date to stop retrieving commits from.
    """

    url = "repository/commits?per_page=25"
    if user_name:
        url += f"&author={user_name}"
    if since:
        url += f"&since={since.isoformat()}"
    if until:
        url += f"&until={until.isoformat()}"

    commits = execute_gitlab_api_request(url)
    return commits


def execute_gitlab_api_request(url: str) -> Dict[str, Any]:

    gitlab_token = os.getenv('GITLAB_PERSONAL_ACCESS_TOKEN')
    gitlab_url = os.getenv('GITLAB_API_URL')
    gitlab_api_project_url = os.getenv('GITLAB_PROJECT_URL')

    request_url = f"{gitlab_url}/projects/{gitlab_api_project_url}/{url}"

    headers = {
        "PRIVATE-TOKEN": gitlab_token
    }

    response = requests.get(request_url, headers=headers)
    if response.status_code == 200:
        response_json = response.json()
        return response_json
    else:
        print(f"Error en la petición: {response.status_code}")
        print(response.text)
        return {"error": response.text, "status_code": response.status_code}

def get_gitlab_agent_additional_tools():
    tools = [
        get_gitlab_issues,
        get_gitlab_project_statistics,
        get_gitlab_braches,
        get_gitlab_project_commits,
        get_gitlab_project_members
    ]
    wrapped_tools = [patch_tool_with_exception_handling(tool) for tool in tools]
    return wrapped_tools