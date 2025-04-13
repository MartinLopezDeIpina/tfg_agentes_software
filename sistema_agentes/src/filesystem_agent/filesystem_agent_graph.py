import asyncio
import json
import os
from typing import TypedDict, List

from langgraph.prebuilt import create_react_agent
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph

from src.filesystem_agent.prompts import filesystem_agent_system_prompt
from src.utils import tab_all_lines_x_times


class State(TypedDict):
    messages: list[BaseMessage]
    query: str

    tools: List[BaseTool]

    result_message: List[BaseMessage]



async def retrieve_info_for_system_message(state: State):
    dir_tool = None
    for tool in state["tools"]:
        if tool.name == "directory_tree":
            dir_tool = tool

    directory_path = os.getenv("FILESYSTEM_DOCS_FOLDER")
    dir_task = dir_tool.ainvoke({
        "path": directory_path
    })

    dir_result = await asyncio.gather(dir_task)
    dir_str = dir_result[0]

    state["messages"].append(
        SystemMessage(
            filesystem_agent_system_prompt.format(
                available_directory=directory_path,
                available_files=dir_str
            )
        )
    )
    state["messages"].append(
        HumanMessage(
            content=state["query"]
        )
    )

    return state


def create_file_system_agent(tools: List[BaseTool]) -> CompiledGraph:

    graph_builder = StateGraph(State)

    react_graph = create_react_agent(model="gpt-4o-mini", tools=tools)

    graph_builder.add_node(retrieve_info_for_system_message)
    graph_builder.add_node("react_graph", react_graph)

    graph_builder.set_entry_point("retrieve_info_for_system_message")
    graph_builder.add_edge("retrieve_info_for_system_message", "react_graph")
    graph_builder.set_finish_point("react_graph")

    graph = graph_builder.compile()
    return graph


