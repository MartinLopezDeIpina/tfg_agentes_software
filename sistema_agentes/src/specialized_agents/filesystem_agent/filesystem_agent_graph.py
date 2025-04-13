import asyncio
import os
from typing import List

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage

from src.specialized_agents.BaseAgent import BaseAgent
from src.specialized_agents.filesystem_agent.prompts import filesystem_agent_system_prompt
from src.mcp_multi_client import MCPClient


class FileSystemAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="file_system_agent",
            description="Agent to interact with the file system",
            model=ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0,
            ),
            tools_str= [
                "search_files",
                "read_file",
                "read_multiple_files",
                "directory_tree"
            ]
        )
        
    async def connect_to_mcp(self):
        self.mcp_client = MCPClient(agent_tools=self.tools_str)
        await self.mcp_client.connect_to_filesystem_server()
        self.tools = self.mcp_client.get_tools()

    async def prepare_prompt(self, query: str) -> List[BaseMessage]:
        dir_tool = None
        for tool in self.tools:
            if tool.name == "directory_tree":
                dir_tool = tool

        directory_path = os.getenv("FILESYSTEM_DOCS_FOLDER")
        dir_task = dir_tool.ainvoke({
            "path": directory_path
        })

        dir_result = await asyncio.gather(dir_task)
        dir_str = dir_result[0]

        messages = [
            SystemMessage(
                filesystem_agent_system_prompt.format(
                    available_directory=directory_path,
                    available_files=dir_str
                )
            ),
            HumanMessage(
                content=query
            )
        ]
        return messages

