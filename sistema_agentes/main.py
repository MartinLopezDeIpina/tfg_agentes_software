import asyncio
from contextlib import AsyncExitStack

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from src.mcp_client.mcp_multi_client import MCPClient
from src.orchestrator_agent.orchestrator_agent_graph import create_orchestrator_graph
from src.planner_agent.planner_agent_graph import create_planner_graph
from src.specialized_agents.code_agent.code_agent_graph import CodeAgent
from src.specialized_agents.confluence_agent.confluence_agent_graph import ConfluenceAgent
from src.specialized_agents.filesystem_agent.filesystem_agent_graph import FileSystemAgent
from src.specialized_agents.gitlab_agent.gitlab_agent_graph import GitlabAgent
from src.specialized_agents.google_drive_agent.google_drive_agent_graph import GoogleDriveAgent


async def main():

    agents = [
        GoogleDriveAgent(),
        FileSystemAgent(),
        #GitlabAgent(),
        ConfluenceAgent(),
        CodeAgent()
    ]

    # crear los agentes conectandolos de forma secuencial -> esto debería hacerse solo al inicio del programa
    available_agents = []
    for agent in agents:
        try:
            await agent.connect_to_mcp()
            available_agents.append(agent)
        except Exception as e:
            print(f"Error conectando agente {agent.name}: {e}")

    """
    orchestrator_graph = create_orchestrator_graph()
    result = await orchestrator_graph.ainvoke({
        "available_agents": available_agents,
        "planner_high_level_plan":"Busca toda la información posible sobre el proyecto",
        "model": ChatOpenAI(model="gpt-4o-mini")
    })
    print(result)
    """

    try:
        planner_graph = create_planner_graph()
        result = await planner_graph.ainvoke({
            "available_agents": available_agents,
            "query": "Qué módulos tiene el proyecto?",
            "planner_model": ChatOpenAI(model="o1-mini"),
            "structure_model": ChatOpenAI(model="gpt-4o-mini"),
            "max_steps": 2,
            "current_step": 0
        })
        print(result)

    finally:
        await MCPClient.cleanup()


if __name__ == '__main__':
    load_dotenv()

    #asyncio.run(ejecutar_agente_codigo("Qué es lo que explica cada notebook de jupyter?"))

    #asyncio.run(execute_confluence_agent("Existe alguna guía de estilos para el proyecto?, si es así, qué color primario se utiliza?"))
    #asyncio.run(execute_confluence_agent("Qué funcionalidades tiene el frontend?"))
    #asyncio.run(execute_gitlab_agent("Qué ramas existen en el proyecto?"))
    #asyncio.run(execute_google_drive_agent("Existe alguna maqueta para la gestión del administrador?"))
    #asyncio.run(execute_filesystem_agent("Existe alguna maqueta para la gestión del administrador?"))
    asyncio.run(main())

