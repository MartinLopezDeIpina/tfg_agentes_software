import asyncio
from typing import List

from dotenv import load_dotenv
from langchain.memory.entity import BaseEntityStore
from langchain_core.stores import InMemoryStore
from langgraph.graph import StateGraph
from langgraph.managed.is_last_step import RemainingSteps
from langsmith import Client

from src.BaseAgent import AgentState
from src.db.documentation_indexer import AsyncPGVectorRetriever
from src.db.langchain_store_utils import delete_all_memory_documents
from src.db.pgvector_utils import PGVectorStore
from src.db.postgres_connection_manager import PostgresPoolManager
from src.evaluators.dataset_utils import create_langsmith_datasets, create_main_agent_memory_partitioned_datasets
from src.formatter_agent.formatter_graph import FormatterAgent
from src.main_agent.main_agent_builder import FlexibleAgentBuilder
from src.main_agent.main_graph import BasicMainAgent , OrchestratorOnlyMainAgent
from src.mcp_client.mcp_multi_client import MCPClient
from src.orchestrator_agent.orchestrator_agent_graph import OrchestratorAgent, DummyOrchestratorAgent, ReactOrchestratorAgent
from src.planner_agent.planner_agent_graph import PlannerAgent, BasicPlannerAgent, OrchestratorPlannerAgent
from src.specialized_agents.SpecializedAgent import SpecializedAgent
from src.specialized_agents.code_agent.code_agent_graph import CodeAgent
from src.specialized_agents.confluence_agent.confluence_agent_graph import ConfluenceAgent, CachedConfluenceAgent
from src.specialized_agents.filesystem_agent.filesystem_agent_graph import FileSystemAgent
from src.specialized_agents.gitlab_agent.gitlab_agent_graph import GitlabAgent
from src.specialized_agents.google_drive_agent.google_drive_agent_graph import GoogleDriveAgent


def get_specialized_agents():
    return [
        GoogleDriveAgent(),
        FileSystemAgent(),
        GitlabAgent(),
        ConfluenceAgent(),
        CodeAgent()
    ]

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

async def evaluate_cached_confluence_agent():
    await evaluate_specialized_agent(CachedConfluenceAgent(use_memory=False))

async def evaluate_code_agent():
    await evaluate_specialized_agent(CodeAgent())

async def evaluate_file_system_agent():
    await evaluate_specialized_agent(FileSystemAgent())

async def evaluate_google_drive_agent():
    await evaluate_specialized_agent(GoogleDriveAgent())

async def evaluate_gitlab_agent():
    await evaluate_specialized_agent(GitlabAgent())

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
    langsmith_client = Client()

    await planner_agent.evaluate_agent(langsmith_client=langsmith_client)

async def evaluate_orchestrator_planner_agent():
    agents = []
    try:
        langsmith_client = Client()

        agents = [
            GoogleDriveAgent(),
            FileSystemAgent(),
            GitlabAgent(),
            ConfluenceAgent(),
            CodeAgent()
        ]

        available_agents = await init_specialized_agents(agents)
        planner_agent = OrchestratorPlannerAgent(available_agents=available_agents)

        await planner_agent.evaluate_agent(langsmith_client=langsmith_client)

    finally:
        await agents[0].cleanup()

async def debug_agent():
    agent = CachedConfluenceAgent()
    try:
        await agent.init_agent()
        await agent.execute_agent_graph_with_exception_handling(input={
            "query":  "Qué sistemas de despliegue hay disponibles?",
            "remaining_steps": RemainingSteps(2)
        })
    except Exception as e:
        print(f"Error ejecutando agente {agent.name}: {e}")
    finally:
        await agent.cleanup()

async def pruebas_pgvector_store():
    store = PGVectorStore(
        collection_name="official_documentation"
    )
    retriever = AsyncPGVectorRetriever(
        pg_vector_store=store
    )
    docs = await retriever.ainvoke(input="LKS next", top_k=5)
    print(docs)

async def call_agent():
    """
    Configuraciones posibles main - planner - orchestrator:
        - orchestrator_only, none, basic
        - orchestrator_only, none, react
        - basic, orchestrator_planner, dummy
        - basic, basic, basic
        - basic, basic, react
    """

    try:
        # Construcción de agente con BasicMain + BasicPlanner + ReactOrchestrator (configuración válida)
        builder = FlexibleAgentBuilder()
        agent = await (await (builder
                       .reset()
                       .with_main_agent_type("basic")
                       .with_planner_type("basic")
                       .with_orchestrator_type("basic")
                       .with_specialized_agents([
                            CodeAgent(use_memory=True),
                            #CachedConfluenceAgent(use_memory=True),
                            #GitlabAgent(use_memory=True),
                            #FileSystemAgent(use_memory=True),
                            #GoogleDriveAgent(use_memory=True),
                        ])
                       .initialize_agents())).build()

        result = await agent.execute_agent_graph_with_exception_handling({
            "query": "Cómo se gestionan las migraciones de la base de datos?",
            "messages": []
        })
    finally:
        await MCPClient.cleanup()

async def evaluate_main_agent(is_prueba: bool = True):
    try:
        builder = FlexibleAgentBuilder()
        ls_client = Client()
        agent = await (await (builder
                        .reset()
                        .with_main_agent_type("basic")
                        .with_planner_type("basic")
                        .with_orchestrator_type("basic")
                        .with_specialized_agents()
                        .with_specialized_agents([
                            CodeAgent(use_memory=True),
                            #CachedConfluenceAgent(use_memory=True),
                            #GitlabAgent(use_memory=True),
                            #FileSystemAgent(use_memory=True),
                            #GoogleDriveAgent(use_memory=True),
                        ])
                        .initialize_agents())).build()
        await agent.evaluate_agent(langsmith_client=ls_client, is_prueba=is_prueba)
        #await agent.evaluate_agent(langsmith_client=ls_client, is_prueba=is_prueba, dataset_name="evaluate_main_agent_memory", dataset_split="test")
    finally:
        await MCPClient.cleanup()
        
async def delete_memory_docs():
    store = (await PostgresPoolManager.get_instance()).get_memory_store()
    await delete_all_memory_documents(store=store)

if __name__ == '__main__':
    load_dotenv()

    #asyncio.run(delete_memory_docs())

    #asyncio.run(debug_agent())
    #create_langsmith_datasets(dataset_prueba=False, agents_to_update=["main_agent"])
    #asyncio.run(evaluate_main_agent(is_prueba=True))

    #asyncio.run(evaluate_orchestrator_planner_agent())
    #asyncio.run(evaluate_cached_confluence_agent())

    #asyncio.run(prueba())
    #clase = ClaseB()
    #asyncio.run(clase.prueba())
    #asyncio.run(call_agent())
    
    asyncio.run(evaluate_main_agent(is_prueba=True))

    #create_main_agent_memory_partitioned_datasets()
