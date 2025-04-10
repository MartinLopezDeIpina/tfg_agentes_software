import asyncio
import json
from typing import TypedDict, List

from langgraph.prebuilt import create_react_agent
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph

from src.confluence_agent.prompts import system_prompt
from src.utils import tab_all_lines_x_times


class State(TypedDict):
    messages: list[BaseMessage]
    query: str

    tools: List[BaseTool]

    result_message: List[BaseMessage]



async def retrieve_info_for_system_message(state: State):
    pages_tool = None
    for tool in state["tools"]:
        if tool.name == "confluence_search":
            pages_tool = tool

    pages_task = pages_tool.ainvoke({
        "query":"type=page",
        "limit": 500
    })

    pages_result = await asyncio.gather(pages_task)
    pages = json.loads(pages_result[0])
    pages_titles = []
    for i, page in enumerate(pages):
        # Si no tiene titulo añadir toda la página
        try:
            title = page["title"]
            id = page["id"]
            pages_titles.append(f"{i}. id: {id}, title: {title}")
        except Exception:
            pages_titles.append(page)

    confluence_pages_preview = "\n".join(pages_titles)
    confluence_pages_preview = tab_all_lines_x_times(confluence_pages_preview)
    state["messages"].append(
        SystemMessage(
            system_prompt.format(
                confluence_pages_preview=confluence_pages_preview
            )
        )
    )
    state["messages"].append(
        HumanMessage(
            content=state["query"]
        )
    )

    return state


def create_confluence_agent(tools: List[BaseTool]) -> CompiledGraph:

    graph_builder = StateGraph(State)

    react_graph = create_react_agent(model="gpt-4o-mini", tools=tools)

    graph_builder.add_node(retrieve_info_for_system_message)
    graph_builder.add_node("react_graph", react_graph)

    graph_builder.set_entry_point("retrieve_info_for_system_message")
    graph_builder.add_edge("retrieve_info_for_system_message", "react_graph")
    graph_builder.set_finish_point("react_graph")

    graph = graph_builder.compile()
    return graph


