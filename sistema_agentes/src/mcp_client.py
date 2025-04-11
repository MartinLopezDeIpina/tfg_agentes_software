import asyncio
from dotenv import load_dotenv
import json
import os
from typing import Optional, List
from contextlib import AsyncExitStack

from langchain_core.tools import BaseTool
from mcp import ClientSession, StdioServerParameters, stdio_client
from mcp.client.sse import sse_client
from mcp.types import Tool
from langchain_mcp_adapters.tools import load_mcp_tools
from config import MCP_CODE_SERVER_DIR, MCP_CODE_SERVER_PORT
from src.gitlab_agent.additional_tools import get_gitlab_issues


class MCPClient:

    host_ip: str
    host_port: int

    tools: List[BaseTool]
    session: ClientSession

    def __init__(self, host_ip: str=MCP_CODE_SERVER_DIR, host_port: int=MCP_CODE_SERVER_PORT):
        self.host_ip = host_ip
        self.host_port = host_port
        # Initialize session and client objects
        self.exit_stack = AsyncExitStack()

    async def connect_to_gitlab_server(self):
        server_command = "npx"
        server_args = ["-y", "@modelcontextprotocol/server-gitlab"]

        server_env = {
            "GITLAB_PERSONAL_ACCESS_TOKEN": os.getenv('GITLAB_PERSONAL_ACCESS_TOKEN'),
            "GITLAB_API_URL": os.getenv('GITLAB_API_URL'),
        }

        if not server_env["GITLAB_API_URL"]:
            raise ValueError("GITLAB_API_URL is not set in the environment variables.")
        if not server_env["GITLAB_PERSONAL_ACCESS_TOKEN"]:
            raise ValueError("GITLAB_PERSONAL_ACCESS_TOKEN is not set in the environment variables.")

        server_params = StdioServerParameters(
            command=server_command,
            args=server_args,
            env=server_env
        )

        print(f"Connecting to server with command: {server_command} {' '.join(server_args)}")
        await self.connect_to_stdio_server(server_params)


    async def connect_to_stdio_server(self, stdio_params: StdioServerParameters):

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(stdio_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

        await self.connect_to_server()

    async def connect_to_sse_server(self):

      print("Connecting to server...")

      streams = await self.exit_stack.enter_async_context(
          sse_client(f"http://{self.host_ip}:{self.host_port}/sse")
      )
      self.session = await self.exit_stack.enter_async_context(
          ClientSession(streams[0], streams[1])
      )
      await self.connect_to_server()


    async def connect_to_server(self):
        await self.session.initialize()

        # Listar herramientas disponibles
        response = await self.session.list_tools()
        tools = response.tools
        self.tools = await load_mcp_tools(self.session)
        print("\nConectado al servidor con herramientas:", [tool.name for tool in tools])

        for tool in tools:
           print(f"Tool: {tool.name}, schema: {tool.inputSchema}")




    async def cleanup(self):
      await self.exit_stack.aclose()

    async def call_tool(self, tool_name, tool_args):

      result = await self.session.call_tool(tool_name, tool_args)

      return result

    def get_tools(self) -> List[BaseTool]:
      return self.tools

async def main():

    client = MCPClient(host_ip="localhost", host_port=9001)

    try:
        await client.connect_to_gitlab_server()

        """
        tool_name="get_code_repository_rag_docs_from_query_tool"
        tool_args = {
            "query": "LLM tools for pgvector"
        }
        tool_name = "get_file_from_repository_tool"
        tool_args = {
            "file_path": "READme.md"
        }

        result = await client.call_tool(tool_name, tool_args)
        print(f"resultado: {result}")

        tool_name = "confluence_search"
        tool_args = {
            "query":"type=page",
            "limit": 50
        }

        result = await client.call_tool(tool_name, tool_args)

        print(f"resultado: {result.content}")
        pages = json.loads(result.content[0].text)
        for page in pages:
            print(page["title"])
            print(page["content"])
            """


        tool_args = {
          "project_id": "lks/genai/ia-core-tools",
          "file_path": "README.md",
          "ref": "develop"
        }
        result = await client.call_tool("get_file_contents", tool_args)
        print(result)

    finally:
        await client.cleanup()

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())