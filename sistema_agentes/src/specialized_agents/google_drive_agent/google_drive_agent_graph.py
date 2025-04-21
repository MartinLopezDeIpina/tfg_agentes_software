from langchain_core.language_models import BaseChatModel

from src.BaseAgent import AgentState
from src.mcp_client.mcp_multi_client import MCPClient
from src.specialized_agents.citations_tool.models import GoogleDriveDataSource
import asyncio
from typing import List

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from src.specialized_agents.SpecializedAgent import SpecializedAgent

from static.agent_descriptions import GOOGLE_DRIVE_AGENT_DESCRIPTION
from static.prompts import CITE_REFERENCES_PROMPT, google_drive_system_prompt

class GoogleDriveAgent(SpecializedAgent):
    def __init__(self, model: BaseChatModel = None):
        super().__init__(
            name="google_drive_agent",
            description=GOOGLE_DRIVE_AGENT_DESCRIPTION,
            model=model,
            tools_str= [
                "gdrive_list_files",
                "gdrive_read_file",
                "gdrive_search",
                "gdrive_list_files_json"
            ],
            data_sources=[GoogleDriveDataSource("gdrive_list_files_json")],
            prompt=CITE_REFERENCES_PROMPT.format(
                agent_prompt=google_drive_system_prompt
            )
        )

    async def connect_to_mcp(self):
        self.mcp_client = MCPClient(agent_tools=self.tools_str)
        await self.mcp_client.connect_to_google_drive_server()
        self.tools = self.mcp_client.get_tools()

    async def prepare_prompt(self, state: AgentState) -> AgentState:
        files_tool = None
        for tool in self.tools:
            if tool.name == "gdrive_list_files":
                files_tool = tool

        files_task = files_tool.ainvoke({})

        files_result = await asyncio.gather(files_task)
        files_str = files_result[0]

        messages = [
            SystemMessage(
                self.prompt.format(
                    google_drive_files_info=files_str
                )
            ),
            HumanMessage(
                content=state["query"]
            )
        ]
        state["messages"] = messages
        return state


