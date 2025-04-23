import os
from requests import Response
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

import requests
from langchain_core.tools import BaseTool, tool

from src.mcp_client.tool_wrapper import patch_tool_with_exception_handling
from config import GITLAB_API_URL, GITLAB_PROJECT_URL


def execute_gitlab_api_request(url: str, params: Dict[str, Any] = None) -> Response:
    """
    Ejecuta una única petición a la API de GitLab sin manejar paginación

    Args:
        url: Endpoint de la API
        params: Parámetros opcionales para la petición

    Returns:
        respuesta de la api
    """
    gitlab_token = os.getenv('GITLAB_PERSONAL_ACCESS_TOKEN')
    request_url = f"{GITLAB_API_URL}/projects/{GITLAB_PROJECT_URL}/{url}"
    headers = {
        "PRIVATE-TOKEN": gitlab_token
    }

    response = requests.get(request_url, headers=headers, params=params)
    return response



def execute_gitlab_api_request_with_pagination(url: str, params: Dict[str, Any] = None) -> List:
    """
    Ejecuta una petición a la API de GitLab con manejo de paginación

    Args:
        url: Endpoint de la API
        params: Parámetros opcionales para la petición

    Returns:
        Lista con todos los elementos combinados de todas las páginas
    """
    if params is None:
        params = {}
    if 'per_page' not in params:
        params['per_page'] = 25
    all_items = []
    page = 1

    while True:
        params["page"] = page

        response = execute_gitlab_api_request(url, params)
        if response.status_code != 200:
            print(f"Error en la petición: {response.status_code}: {response.text}")
            return [{"error": response.text, "status_code": response.status_code}]


        current_page_items = response.json()
        all_items.extend(current_page_items)

        headers = response.headers
        if not headers:
            break

        if 'X-Next-Page' in headers and headers['X-Next-Page']:
            page = int(headers['X-Next-Page'])
        else:
            break

    return all_items


@tool
def get_gitlab_issues(issue_ids: List[int] = None):
    """
    Get the issues from the GitLab repository.
    If not issue_ids are provided, it will return all issues.

    Args:
        issue_ids (List[int]): List of issue IDs to retrieve.
    """
    params = {}
    if issue_ids and len(issue_ids) > 0:
        params['iids[]'] = issue_ids

    return execute_gitlab_api_request_with_pagination("issues", params)


@tool
def get_gitlab_project_statistics():
    """
    Get the statistics of the GitLab project, including the number of issues, merge requests, and users.
    """
    response = execute_gitlab_api_request_with_pagination("")
    return response


@tool
def get_gitlab_project_members():
    """
    Get the project's member information.
    This includes the user name, id and role among others.
    """
    return execute_gitlab_api_request_with_pagination("members")


@tool
def get_gitlab_braches():
    """
    Get the available branches of the GitLab repository.
    """
    return execute_gitlab_api_request_with_pagination("repository/branches")


@tool
def get_gitlab_project_commits(user_name: Optional[str] = None, since: Optional[datetime] = None,
                               until: Optional[datetime] = None, result_limit: int = 25):
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
    params = {'per_page': result_limit}

    if user_name:
        params['author'] = user_name
    if since:
        params['since'] = since.isoformat()
    if until:
        params['until'] = until.isoformat()

    return execute_gitlab_api_request_with_pagination("repository/commits", params)


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