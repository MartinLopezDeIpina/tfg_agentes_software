import asyncio
from typing import TypedDict, List

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph

from src.BaseAgent import AgentState
from src.mcp_client.mcp_multi_client import MCPClient
from src.specialized_agents.SpecializedAgent import SpecializedAgent
from src.specialized_agents.gitlab_agent.additional_tools import get_gitlab_agent_additional_tools
from src.specialized_agents.gitlab_agent.prompts import gitlab_agent_system_prompt
from static.agent_descriptions import GITLAB_AGENT_DESCRIPTION

class GitlabAgent(SpecializedAgent):
    def __init__(self, model: BaseChatModel = None):
        super().__init__(
            name="gitlab_agent",
            description=GITLAB_AGENT_DESCRIPTION,
            model=model,
            tools_str= [
                "gdrive_list_files",
                "gdrive_read_file"
            ]
        )

    async def connect_to_mcp(self):
        self.mcp_client = MCPClient(agent_tools=self.tools_str)
        await self.mcp_client.connect_to_gitlab_server()
        self.tools = self.mcp_client.get_tools()
        self.tools.extend(get_gitlab_agent_additional_tools())

    async def prepare_prompt(self, state: AgentState) -> AgentState:
        stats_tool = None
        for tool in self.tools:
            if tool.name == "get_gitlab_project_statistics":
                stats_tool = tool

        stats_task = stats_tool.ainvoke({})

        stats_result = await asyncio.gather(stats_task)

        messages = [
            SystemMessage(
                gitlab_agent_system_prompt.format(
                    gitlab_project_statistics=stats_result
                )
            ),
            HumanMessage(
                content=state["query"]
            )
        ]
        state["messages"] = messages
        return state
