from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from src.code_agent.code_agent_graph import create_code_agent_graph
from src.mcp_client import MCPClient

def print_stream(stream):
    for s in stream:
        message = s["messages"][-1]
        if isinstance(message, tuple):
            print(message)
        else:
            message.pretty_print()


async def ejecutar_agente():

    mcp_client = MCPClient()

    try:
        await mcp_client.connect_to_server()

        tools = mcp_client.get_tools()
        model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        graph = create_react_agent(model, tools=tools, debug=True)

        inputs = {"messages": [("user", "Cúales son las tools para usar agentes LLM que hay en el proyecto?")]}
        async for chunk in graph.astream(inputs):
            print(chunk)

        


    finally:
        await mcp_client.cleanup()

async def ejecutar_agente_codigo(query: str):
    mcp_client = MCPClient()

    try:
        await mcp_client.connect_to_server()

        tools = mcp_client.get_tools()
        model = ChatOpenAI(model="gpt-4o-mini", temperature=0)

        graph = create_code_agent_graph(tools)

        result = await graph.ainvoke({
            "query": query,
            "tools": tools,
            "messages": [],
        })


    finally:
        await mcp_client.cleanup()


