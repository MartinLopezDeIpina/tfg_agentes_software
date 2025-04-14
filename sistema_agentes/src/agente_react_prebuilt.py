from src.specialized_agents.code_agent.code_agent_graph import create_code_agent_graph
from src.specialized_agents.confluence_agent.confluence_agent_graph import create_confluence_agent
from src.specialized_agents.google_drive_agent.google_drive_agent_graph import create_google_drive_agent
from src.specialized_agents.gitlab_agent.additional_tools import get_gitlab_issues, get_gitlab_project_statistics, get_gitlab_braches, \
    get_gitlab_project_members, get_gitlab_project_commits
from src.specialized_agents.gitlab_agent.gitlab_agent_graph import create_gitlab_agent
from src.mcp_client.mcp_multi_client import MCPClient

def print_stream(stream):
    for s in stream:
        message = s["messages"][-1]
        if isinstance(message, tuple):
            print(message)
        else:
            message.pretty_print()


async def ejecutar_agente_codigo(query: str):
    mcp_client = MCPClient()

    try:
        await mcp_client.connect_to_sse_server(
            host_ip="localhost",
            host_port=8000
        )

        tools = mcp_client.get_tools()

        graph = create_code_agent_graph(tools)

        result = await graph.ainvoke({
            "query": query,
            "tools": tools,
            "messages": [],
        })

    finally:
        await mcp_client.cleanup()

async def execute_confluence_agent(query: str):
    mcp_client = MCPClient()

    try:
        await mcp_client.connect_to_sse_server(
            host_ip="localhost",
            host_port=9000
        )

        tools = mcp_client.get_tools()
        available_tools = []
        for tool in tools:
            if tool.name == "confluence_search" or tool.name == "confluence_get_page":
                available_tools.append(tool)

        graph = create_confluence_agent(available_tools)

        result = await graph.ainvoke({
            "query": query,
            "tools": available_tools,
            "messages": [],
        })

    finally:
        await mcp_client.cleanup()
        
async def execute_gitlab_agent(query: str):

    mcp_client = MCPClient()

    try:
        await mcp_client.connect_to_gitlab_server()

        tools = mcp_client.get_tools()
        available_tools = []
        for tool in tools:
            if tool.name == "get_file_contents" or tool.name == "create_issue":
                available_tools.append(tool)

        available_tools.append(get_gitlab_issues)
        available_tools.append(get_gitlab_project_statistics)
        available_tools.append(get_gitlab_braches)
        available_tools.append(get_gitlab_project_members)
        available_tools.append(get_gitlab_project_commits)

        graph = create_gitlab_agent(available_tools)

        result = await graph.ainvoke({
            "query": query,
            "tools": available_tools,
            "messages": [],
        })

    finally:
        await mcp_client.cleanup()

async def execute_google_drive_agent(query: str):
    mcp_client = MCPClient()

    try:
        await mcp_client.connect_to_google_drive_server()

        tools = mcp_client.get_tools()
        available_tools = []
        for tool in tools:
            if tool.name == "gdrive_list_files" or tool.name == "gdrive_read_file":
                available_tools.append(tool)



        graph = create_google_drive_agent(tools)

        result = await graph.ainvoke({
            "query": query,
            "tools": tools,
            "messages": [],
        })

    finally:
        await mcp_client.cleanup()

