import asyncio
from typing import TypedDict, List

from langchain_core.language_models import BaseChatModel
from langchain_core.stores import BaseStore
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph

from src.BaseAgent import AgentState
from src.mcp_client.mcp_multi_client import MCPClient
from src.specialized_agents.SpecializedAgent import SpecializedAgent, SpecializedAgentState
from src.specialized_agents.citations_tool.models import GitLabDataSource
from src.specialized_agents.gitlab_agent.additional_tools import get_gitlab_agent_additional_tools
from static.agent_descriptions import GITLAB_AGENT_DESCRIPTION
from static.prompts import CITE_REFERENCES_PROMPT, gitlab_agent_system_prompt


class GitlabAgent(SpecializedAgent):
    def __init__(self, model: BaseChatModel = None, use_memory: bool = False):
        super().__init__(
            name="gitlab_agent",
            description=GITLAB_AGENT_DESCRIPTION,
            model=model,
            tools_str= [
                """
                Obtenerlas manualmente en lugar de MCP
                """
            ],
            prompt_only_tools=[
                "get_gitlab_project_statistics"
            ],
            data_sources=[GitLabDataSource(
                get_documents_tool_name=["get_gitlab_project_commits", "get_gitlab_issues"],
                tool_args = [
                    {
                       "result_limit": 500 
                    },
                    {
                        
                    }
                ]
            )],
            prompt=CITE_REFERENCES_PROMPT.format(
                agent_prompt=gitlab_agent_system_prompt
            ),
            use_memory=use_memory
        )

    async def connect_to_mcp(self):
        self.mcp_client = MCPClient.get_instance()
        await self.mcp_client.connect_to_gitlab_server()

        self.mcp_client.register_agent(self.name, self.tools_str)
        self.tools = self.mcp_client.get_agent_tools(self.name)

    async def add_additional_tools(self):
        self.tools.extend(get_gitlab_agent_additional_tools())

    async def prepare_prompt(self, state: SpecializedAgentState, store = None) -> SpecializedAgentState:
        state = await super().prepare_prompt(state=state, store=store)
        stats_tool = None
        for tool in self.tools:
            if tool.name == "get_gitlab_project_statistics":
                stats_tool = tool

        stats_task = stats_tool.ainvoke({})
        stats_result = await asyncio.gather(stats_task)

        messages = [
            SystemMessage(
                self.prompt.format(
                    gitlab_project_statistics=stats_result,
                    memory_docs=state.get("memory_docs")
                )
            ),
            HumanMessage(
                content=state["query"]
            )
        ]
        state["messages"] = messages
        return state
