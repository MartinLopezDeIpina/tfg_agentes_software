import asyncio
from random import random
from typing import TypedDict, List

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from src.BaseAgent import AgentState
from src.mcp_client.mcp_multi_client import MCPClient
from src.specialized_agents.citations_tool.models import CodeDataSource
from static.agent_descriptions import CODE_AGENT_DESCRIPTION

from src.specialized_agents.SpecializedAgent import SpecializedAgent
from static.prompts import CITE_REFERENCES_PROMPT, code_agent_system_prompt


class CodeAgent(SpecializedAgent):
    def __init__(self, model: BaseChatModel = None):
        super().__init__(
            name="code_agent",
            description=CODE_AGENT_DESCRIPTION,
            model=model,
            tools_str= [
                "get_code_repository_rag_docs_from_query_tool",
                "get_file_from_repository_tool",
                "get_repository_tree_tool",
                "get_all_respository_files_list"
            ],
            prompt_only_tools=[
                "get_repository_tree_tool",
                "get_all_respository_files_list"
            ],
            data_sources=[CodeDataSource(
                get_documents_tool_name="get_all_respository_files_list",
                tool_args={}
            )],
            prompt=CITE_REFERENCES_PROMPT.format(
                agent_prompt=code_agent_system_prompt
            )
        )

    async def connect_to_mcp(self):
        self.mcp_client = MCPClient.get_instance()
        await self.mcp_client.connect_to_code_server()

        self.mcp_client.register_agent(self.name, self.tools_str)
        self.tools = self.mcp_client.get_agent_tools(self.name)

    async def prepare_prompt(self, state: AgentState) -> AgentState:
        rag_tool = None
        tree_tool = None
        for tool in self.tools:
            if tool.name == "get_code_repository_rag_docs_from_query_tool":
                rag_tool = tool
            elif tool.name == "get_repository_tree_tool":
                tree_tool = tool

        tree_task = tree_tool.ainvoke({})
        rag_task = rag_tool.ainvoke({
            "query": state["query"]
        })

        proyect_tree, initial_retrieved_docs = await asyncio.gather(tree_task, rag_task)

        messages = [
            SystemMessage(
                self.prompt.format(
                    proyect_tree=proyect_tree,
                    initial_retrieved_docs=initial_retrieved_docs
                )
            ),
            HumanMessage(
                content=state["query"]
            )

        ]
        state["messages"] = messages
        return state
