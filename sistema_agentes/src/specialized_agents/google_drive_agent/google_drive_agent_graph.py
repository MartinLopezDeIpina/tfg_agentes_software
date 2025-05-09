from langchain_core.language_models import BaseChatModel

from src.BaseAgent import AgentState
from src.mcp_client.mcp_multi_client import MCPClient
from src.specialized_agents.citations_tool.models import GoogleDriveDataSource
import asyncio
from typing import List

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from src.specialized_agents.SpecializedAgent import SpecializedAgent, SpecializedAgentState

from static.agent_descriptions import GOOGLE_DRIVE_AGENT_DESCRIPTION
from static.prompts import CITE_REFERENCES_PROMPT, google_drive_system_prompt

class GoogleDriveAgent(SpecializedAgent):
    def __init__(self, model: BaseChatModel = None, use_memory: bool = False):
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
            prompt_only_tools=[
                "gdrive_list_files",
                "gdrive_list_files_json"
            ],
            data_sources=[GoogleDriveDataSource("gdrive_list_files_json")],
            prompt=CITE_REFERENCES_PROMPT.format(
                agent_prompt=google_drive_system_prompt
            ),
            use_memory=use_memory
        )

    async def connect_to_mcp(self):
        self.mcp_client = MCPClient.get_instance()
        await self.mcp_client.connect_to_google_drive_server()

        self.mcp_client.register_agent(self.name, self.tools_str)
        self.tools = self.mcp_client.get_agent_tools(self.name)

    async def prepare_prompt(self, state: SpecializedAgentState, store = None) -> AgentState:
        state = await super().prepare_prompt(state=state, store=store)
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
                    google_drive_files_info=files_str,
                    memory_docs=state.get("memory_docs")
                )
            ),
            HumanMessage(
                content=state["query"]
            )
        ]
        state["messages"] = messages
        return state


