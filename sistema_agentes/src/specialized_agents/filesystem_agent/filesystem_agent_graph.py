import asyncio
import os
from typing import List

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage

from config import OFFICIAL_DOCS_RELATIVE_PATH, REPO_ROOT_ABSOLUTE_PATH
from src.BaseAgent import AgentState
from src.specialized_agents.SpecializedAgent import SpecializedAgent, SpecializedAgentState
from src.specialized_agents.citations_tool.models import CodeDataSource, FileSystemDataSource
from src.mcp_client.mcp_multi_client import MCPClient
from src.specialized_agents.filesystem_agent.additional_tools import get_docs_rag_tool, \
    get_file_system_agent_additional_tools
from static.agent_descriptions import FILE_SYSTEM_AGENT_DESCRIPTION
from static.prompts import CITE_REFERENCES_PROMPT, filesystem_agent_system_prompt


class FileSystemAgent(SpecializedAgent):
    def __init__(self, model: BaseChatModel = None, use_memory: bool = False):
        super().__init__(
            name="file_system_agent",
            description=FILE_SYSTEM_AGENT_DESCRIPTION,
            model=model,
            tools_str= [
                "search_files",
                "read_file",
                "read_multiple_files",
                "directory_tree",
                "rag_search_documentation"
            ],
            prompt_only_tools=[
                "search_files",
                "directory_tree",
            ],
            data_sources=[FileSystemDataSource(
                get_documents_tool_name="search_files",
                tool_args = {
                    "pattern": "",
                    "path": f"{REPO_ROOT_ABSOLUTE_PATH}{OFFICIAL_DOCS_RELATIVE_PATH}"
                }
            )],
            prompt=CITE_REFERENCES_PROMPT.format(
                agent_prompt=filesystem_agent_system_prompt
            ),
            use_memory=use_memory
        )

    async def connect_to_mcp(self):
        self.mcp_client = MCPClient.get_instance()
        await self.mcp_client.connect_to_filesystem_server()

        self.mcp_client.register_agent(self.name, self.tools_str)
        self.tools = self.mcp_client.get_agent_tools(self.name)

    async def add_additional_tools(self):
        additional_tools = await get_file_system_agent_additional_tools()
        self.tools.extend(additional_tools)

    async def prepare_prompt(self, state: SpecializedAgentState, store = None) -> SpecializedAgentState:
        state = await super().prepare_prompt(state=state, store=store)
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
                self.prompt.format(
                    available_directory=directory_path,
                    available_files=dir_str,
                    memory_docs=state.get("memory_docs")
                )
            ),
            HumanMessage(
                content=state["query"]
            )
        ]
        state["messages"] = messages
        return state

