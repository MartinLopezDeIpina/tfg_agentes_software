import asyncio
import json
from typing import TypedDict, List

from IPython.core.release import author
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph

from src.google_drive_agent.prompts import google_drive_system_prompt
from src.gitlab_agent.prompts import gitlab_agent_system_prompt
from src.utils import tab_all_lines_x_times


class State(TypedDict):
    messages: list[BaseMessage]
    query: str

    tools: List[BaseTool]

    result_message: List[BaseMessage]

async def retrieve_info_for_system_message(state: State):
    files_tool = None
    for tool in state["tools"]:
        if tool.name == "gdrive_list_files":
            files_tool = tool

    files_task = files_tool.ainvoke({})

    files_result = await asyncio.gather(files_task)
    files_str = files_result[0]

    state["messages"].append(
        SystemMessage(
            google_drive_system_prompt.format(
                google_drive_files_info=files_str
            )
        )
    )
    state["messages"].append(
        HumanMessage(
            content=state["query"]
        )
    )

    return state


def create_google_drive_agent(tools: List[BaseTool]) -> CompiledGraph:

    graph_builder = StateGraph(State)

    react_graph = create_react_agent(model="gpt-4o-mini", tools=tools)

    graph_builder.add_node(retrieve_info_for_system_message)
    graph_builder.add_node("react_graph", react_graph)

    graph_builder.set_entry_point("retrieve_info_for_system_message")
    graph_builder.add_edge("retrieve_info_for_system_message", "react_graph")
    graph_builder.set_finish_point("react_graph")

    graph = graph_builder.compile()
    return graph


