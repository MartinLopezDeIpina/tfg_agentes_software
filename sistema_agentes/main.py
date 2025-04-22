import asyncio
from contextlib import AsyncExitStack
from typing import List

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langsmith import Client

from src.formatter_agent.formatter_graph import FormatterAgent
from src.main_graph import MainAgent
from src.mcp_client.mcp_multi_client import MCPClient
from src.orchestrator_agent.orchestrator_agent_graph import  OrchestratorAgent
from src.planner_agent.planner_agent_graph import  PlannerAgent
from src.specialized_agents.SpecializedAgent import SpecializedAgent
from src.specialized_agents.code_agent.code_agent_graph import CodeAgent
from src.specialized_agents.confluence_agent.confluence_agent_graph import ConfluenceAgent
from src.specialized_agents.filesystem_agent.filesystem_agent_graph import FileSystemAgent
from src.specialized_agents.gitlab_agent.gitlab_agent_graph import GitlabAgent
from src.specialized_agents.google_drive_agent.google_drive_agent_graph import GoogleDriveAgent
from src.eval_agents.dataset_utils import create_langsmith_datasets

async def main():

    specialized_agents = [
        #GoogleDriveAgent(),
        FileSystemAgent(),
        #GitlabAgent(),
        #ConfluenceAgent(),
        #CodeAgent()
    ]

    try:
        # crear los agentes conectandolos de forma secuencial -> esto debería hacerse solo al inicio del programa
        available_agents = await init_specialized_agents(specialized_agents)

        planner_agent = PlannerAgent()
        orchestrator_agent = OrchestratorAgent(available_agents)
        formatter_agent = FormatterAgent()
        main_agent = MainAgent(
            planner_agent=planner_agent,
            orchestrator_agent=orchestrator_agent,
            formatter_agent=formatter_agent
        )

        main_graph = main_agent.create_graph()
        result = await main_graph.ainvoke({
            "query": "Podrías decirme cada cuanto se hacen reuniones en el proyecto?",
            "messages": []
        })
        """
        orchestrator_graph = orchestrator_agent.create_graph()
        result = await orchestrator_graph.ainvoke({
            "planner_high_level_plan": "Explicame el funcionamiento de la plantilla de admin"
        })
        """

    finally:
        await MCPClient.cleanup()

async def init_specialized_agents(specialized_agents: List[SpecializedAgent]) -> List[SpecializedAgent]:
    available_agents = []
    for agent in specialized_agents:
        try:
            await agent.init_agent()
            available_agents.append(agent)
        except Exception as e:
            print(f"Error conectando agente {agent.name}: {e}")
    return available_agents


async def evaluate_specialized_agent(agent: SpecializedAgent):
    try:
        await agent.init_agent()
        langsmith_client = Client()

        results = await agent.evaluate_agent(langsmith_client=langsmith_client)
        print(results)

    finally:
        await agent.cleanup()

async def evaluate_confluence_agent():
    await evaluate_specialized_agent(ConfluenceAgent())

async def evaluate_code_agent():
    await evaluate_specialized_agent(CodeAgent())

async def evaluate_file_system_agent():
    await evaluate_specialized_agent(FileSystemAgent())

async def evaluate_google_drive_agent():
    await evaluate_specialized_agent(GoogleDriveAgent())

async def evaluate_orchestrator_agent(agents: List[SpecializedAgent] = None):
    try:

        agents = [
            GoogleDriveAgent(),
            FileSystemAgent(),
            GitlabAgent(),
            ConfluenceAgent(),
            CodeAgent()
        ]

        available_agents = await init_specialized_agents(agents)
        orchestrator_agent = OrchestratorAgent(available_agents)

        agents_str = ""
        for agent in available_agents:
            agents_str += f"{agent.name}\n"
        print(f"Evaluando agente orquestador con agentes: \n{agents}")

        langsmith_client = Client()
        await orchestrator_agent.evaluate_agent(langsmith_client=langsmith_client)

    finally:
        await agents[0].cleanup()

async def evaluate_planner_agent():
    planner_agent = PlannerAgent()
    lansmith_client = Client()

    await planner_agent.evaluate_agent(langsmith_client=lansmith_client)

async def evaluate_main_agent():
    specialized_agents = [
        #GoogleDriveAgent(),
        FileSystemAgent(),
        #GitlabAgent(),
        ConfluenceAgent(),
        CodeAgent()
    ]

    try:
        # crear los agentes conectandolos de forma secuencial -> esto debería hacerse solo al inicio del programa
        available_agents = await init_specialized_agents(specialized_agents)

        planner_agent = PlannerAgent()
        orchestrator_agent = OrchestratorAgent(available_agents)
        formatter_agent = FormatterAgent()
        main_agent = MainAgent(
            planner_agent=planner_agent,
            orchestrator_agent=orchestrator_agent,
            formatter_agent=formatter_agent
        )

        langsmith_client = Client()
        await main_agent.evaluate_agent(langsmith_client=langsmith_client)
    finally:
        await specialized_agents[0].cleanup()




if __name__ == '__main__':
    load_dotenv()

    asyncio.run(main())
    #create_langsmith_datasets()
    #asyncio.run(evaluate_google_drive_agent())


