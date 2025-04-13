import asyncio
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from src.orchestrator_agent.orchestrator_agent_graph import create_orchestrator_graph
from src.specialized_agents.filesystem_agent.filesystem_agent_graph import FileSystemAgent


async def main():

    fs_agent = FileSystemAgent()
    await fs_agent.connect_to_mcp()
    
    orchestrator_graph = create_orchestrator_graph()
    result = await orchestrator_graph.ainvoke({
        "available_agents": [fs_agent],
        "planner_high_level_plan":"Busca información sobre documentación del proyecto",
        "model": ChatOpenAI(model="gpt-4o-mini")
    })
    print(result)

    await fs_agent.cleanup()

    """
    reasoner = ChatOpenAI(model="o1-mini")
    query = "Creame un plan breve para estudiar para un examen de matemáticas"

    result = await reasoner.ainvoke(
        input=query
    )
    print("debug")
    """

if __name__ == '__main__':
    load_dotenv()

    #asyncio.run(ejecutar_agente_codigo("Qué es lo que explica cada notebook de jupyter?"))

    #asyncio.run(execute_confluence_agent("Existe alguna guía de estilos para el proyecto?, si es así, qué color primario se utiliza?"))
    #asyncio.run(execute_confluence_agent("Qué funcionalidades tiene el frontend?"))
    #asyncio.run(execute_gitlab_agent("Qué ramas existen en el proyecto?"))
    #asyncio.run(execute_google_drive_agent("Existe alguna maqueta para la gestión del administrador?"))
    #asyncio.run(execute_filesystem_agent("Existe alguna maqueta para la gestión del administrador?"))

    asyncio.run(main())

