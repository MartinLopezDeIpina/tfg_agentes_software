import asyncio
from typing import Optional, List
from contextlib import AsyncExitStack

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.types import Tool
from langchain_mcp_adapters.tools import load_mcp_tools

SERVER_IP="localhost"
SERVER_PORT=8000

class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.tools = None

    async def connect_to_server(self):

      print("Connecting to server...")

      streams = await self.exit_stack.enter_async_context(
          sse_client(f"http://{SERVER_IP}:{SERVER_PORT}/sse")
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

    async def cleanup(self):
      await self.exit_stack.aclose()

    async def call_tool(self, tool_name, tool_args):

      result = await self.session.call_tool(tool_name, tool_args)

      return result

    def get_tools(self) -> List[Tool]:
      return self.tools

async def main():

    client = MCPClient()

    try:
        await client.connect_to_server()

        """
        tool_name="get_code_repository_rag_docs_from_query_tool"
        tool_args = {
            "query": "LLM tools for pgvector"
        }
        """
        tool_name = "get_file_from_repository_tool"
        tool_args = {
            "file_path": "READme.md"
        }

        result = await client.call_tool(tool_name, tool_args)
        print(f"resultado: {result}")

    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())