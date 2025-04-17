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
        ConfluenceAgent(),
        #CodeAgent()
    ]

    try:
        # crear los agentes conectandolos de forma secuencial -> esto debería hacerse solo al inicio del programa
        available_agents = []
        for agent in specialized_agents:
            try:
                await agent.connect_to_mcp()
                available_agents.append(agent)
            except Exception as e:
                print(f"Error conectando agente {agent.name}: {e}")

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
            "query": "Cómo funciona el frontend?",
            "messages": []
        })
        print(result)

    finally:
        await MCPClient.cleanup()

async def evaluate_agent():
    confluence_agent = ConfluenceAgent()
    try:
        await confluence_agent.connect_to_mcp()

        langsmith_client = Client()

        results = await confluence_agent.evaluate_agent(langsmith_client=langsmith_client)
        print(results)

    finally:
        await confluence_agent.cleanup()







if __name__ == '__main__':
    load_dotenv()

    asyncio.run(main())
    #create_langsmith_datasets()
    #asyncio.run(evaluate_agent())


