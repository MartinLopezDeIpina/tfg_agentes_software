
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
from src.specialized_agents.rag_agent.additional_tools import get_rag_agent_additional_tools
from static.agent_descriptions import FILE_SYSTEM_AGENT_DESCRIPTION
from static.prompts import CITE_REFERENCES_PROMPT, filesystem_agent_system_prompt, MEMORIES_PROMPT, \
    rag_agent_system_prompt

class RagAgent(SpecializedAgent):
    """
    Simple rag agent for basic RAG system evaluation
    """
    def __init__(self, model: BaseChatModel = None, use_memory: bool = False):
        super().__init__(
            name="rag_agent",
            description="None",
            model=model,
            tools_str= [
                "rag_search_general_documentation",
                "get_rag_visual_docs_tool",
                "rag_search_documentation"
                "get_code_repository_rag_docs_from_query_tool",
                "get_file_from_repository_tool",
                "get_repository_tree_tool",
                "get_all_respository_files_list"
            ],
            prompt_only_tools=[
            ],
            data_sources=[FileSystemDataSource(
                get_documents_tool_name="rag_full",
                tool_args = {
                    "pattern": "",
                    "path": f"{REPO_ROOT_ABSOLUTE_PATH}{OFFICIAL_DOCS_RELATIVE_PATH}"
                }
            )],
            prompt=CITE_REFERENCES_PROMPT.format(
                agent_prompt=rag_agent_system_prompt,
                memories_prompt=MEMORIES_PROMPT if use_memory else ""
            ),
            use_memory=use_memory
        )

    async def connect_to_mcp(self):
        self.mcp_client = MCPClient.get_instance()
        await self.mcp_client.connect_to_code_server()

        self.mcp_client.register_agent(self.name, self.tools_str)
        self.tools = self.mcp_client.get_agent_tools(self.name)

    async def add_additional_tools(self):
        additional_tools = await get_rag_agent_additional_tools()
        self.tools.extend(additional_tools)

    async def prepare_prompt(self, state: SpecializedAgentState, store = None) -> SpecializedAgentState:
        state = await super().prepare_prompt(state=state, store=store)
        messages = [
                       SystemMessage(
                           self.prompt
                       )
                   ] + state.get("memory_docs") + [
                       HumanMessage(
                           content=state["query"]
                       )
                   ]
        state["messages"] = messages
        return state
