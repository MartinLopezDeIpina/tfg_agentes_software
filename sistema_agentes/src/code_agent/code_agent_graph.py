import asyncio
from typing import TypedDict, List
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_core.tools import BaseTool
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import create_react_agent
from src.code_agent.prompts import system_prompt


class State(TypedDict):
    messages: list[BaseMessage]
    query: str

    tools: List[BaseTool]



async def retrieve_info_for_system_message(state: State):
    rag_tool = None
    tree_tool = None
    for tool in state["tools"]:
        if tool.name == "get_code_repository_rag_docs_from_query_tool":
            rag_tool = tool
        elif tool.name == "get_repository_tree_tool":
            tree_tool = tool

    tree_task = tree_tool.ainvoke({})
    rag_task = rag_tool.ainvoke({
        "query": state["query"]
    })

    proyect_tree, initial_retrieved_docs = await asyncio.gather(tree_task, rag_task)
    
    state["messages"].append(
        SystemMessage(
            system_prompt.format(
                proyect_tree=proyect_tree,
                initial_retrieved_docs=initial_retrieved_docs
            )
        )
    )
    state["messages"].append(
        HumanMessage(
            content=state["query"]
        )
    )

    return state


def create_code_agent_graph(tools: List[BaseTool]) -> CompiledGraph:

    graph_builder = StateGraph(State)

    react_graph = create_react_agent(model="gpt-4o-mini", tools=tools)

    graph_builder.add_node(retrieve_info_for_system_message)
    graph_builder.add_node("react_graph", react_graph)

    graph_builder.set_entry_point("retrieve_info_for_system_message")
    graph_builder.add_edge("retrieve_info_for_system_message", "react_graph")
    graph_builder.set_finish_point("react_graph")

    graph = graph_builder.compile()
    return graph


