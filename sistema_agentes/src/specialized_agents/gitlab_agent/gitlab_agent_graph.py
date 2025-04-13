import asyncio
from typing import TypedDict, List

from langgraph.prebuilt import create_react_agent
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph

from src.specialized_agents.gitlab_agent.prompts import gitlab_agent_system_prompt


class State(TypedDict):
    messages: list[BaseMessage]
    query: str

    tools: List[BaseTool]

    result_message: List[BaseMessage]

async def retrieve_info_for_system_message(state: State):
    stats_tool = None
    for tool in state["tools"]:
        if tool.name == "get_gitlab_project_statistics":
            stats_tool = tool

    stats_task = stats_tool.ainvoke({})

    stats_result = await asyncio.gather(stats_task)

    state["messages"].append(
        SystemMessage(
            gitlab_agent_system_prompt.format(
                gitlab_project_statistics=stats_result
            )
        )
    )
    state["messages"].append(
        HumanMessage(
            content=state["query"]
        )
    )

    return state




def create_gitlab_agent(tools: List[BaseTool]) -> CompiledGraph:

    graph_builder = StateGraph(State)

    react_graph = create_react_agent(model="gpt-4o-mini", tools=tools)

    graph_builder.add_node(retrieve_info_for_system_message)
    graph_builder.add_node("react_graph", react_graph)

    graph_builder.set_entry_point("retrieve_info_for_system_message")
    graph_builder.add_edge("retrieve_info_for_system_message", "react_graph")
    graph_builder.set_finish_point("react_graph")

    graph = graph_builder.compile()
    return graph


