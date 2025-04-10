import asyncio
import json
from typing import Optional, List
from contextlib import AsyncExitStack

from langchain_core.tools import BaseTool
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.types import Tool
from langchain_mcp_adapters.tools import load_mcp_tools
from config import MCP_CODE_SERVER_DIR, MCP_CODE_SERVER_PORT


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

    async def connect_to_server(self):

      print("Connecting to server...")

      streams = await self.exit_stack.enter_async_context(
          sse_client(f"http://{self.host_ip}:{self.host_port}/sse")
      )
      self.session = await self.exit_stack.enter_async_context(
          ClientSession(streams[0], streams[1])
      )
       
      await self.session.initialize()
      print("Session initialized")

      response = await self.session.list_tools()
      print(f"respuesta: {response}")
      tools = response.tools
      print(type(tools[0]))
      self.tools = await load_mcp_tools(self.session)
      print("\nConnected to server with tools:", [tool.name for tool in tools])

    """
      for tool in tools:
          print(f"Tool: {tool.name}, schema: {tool.inputSchema}")
    """



    async def cleanup(self):
      await self.exit_stack.aclose()

    async def call_tool(self, tool_name, tool_args):

      result = await self.session.call_tool(tool_name, tool_args)

      return result

    def get_tools(self) -> List[BaseTool]:
      return self.tools

async def main():

    client = MCPClient(host_ip="localhost", host_port=9000)

    try:
        await client.connect_to_server()

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
        """

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

    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())