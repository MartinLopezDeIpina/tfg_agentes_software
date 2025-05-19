import asyncio
import os
from typing import List

from dotenv import load_dotenv
from langgraph.managed.is_last_step import RemainingSteps
from langsmith import Client
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline

from config import default_llm
from src.db.documentation_indexer import AsyncPGVectorRetriever
from src.db.langchain_store_utils import delete_all_memory_documents
from src.db.pgvector_utils import PGVectorStore
from src.db.postgres_connection_manager import PostgresPoolManager
from src.difficulty_classifier_agent.double_main_agent import DoubleMainAgent
from src.evaluators.dataset_utils import create_question_classifier_dataset, create_langsmith_datasets
from src.main_agent.main_agent_builder import FlexibleAgentBuilder
from src.mcp_client.mcp_multi_client import MCPClient
from src.orchestrator_agent.orchestrator_agent_graph import OrchestratorAgent
from src.planner_agent.planner_agent_graph import PlannerAgent, OrchestratorPlannerAgent
from src.specialized_agents.SpecializedAgent import SpecializedAgent
from src.specialized_agents.code_agent.code_agent_graph import CodeAgent
from src.specialized_agents.confluence_agent.confluence_agent_graph import ConfluenceAgent, CachedConfluenceAgent
from src.difficulty_classifier_agent.difficulty_classifier_graph import ClassifierAgent
from src.specialized_agents.filesystem_agent.filesystem_agent_graph import FileSystemAgent
from src.specialized_agents.gitlab_agent.gitlab_agent_graph import GitlabAgent
from src.specialized_agents.google_drive_agent.google_drive_agent_graph import GoogleDriveAgent
from langchain_huggingface.llms import HuggingFacePipeline
from huggingface_hub import login


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
                        .with_main_agent_type("orchestrator_only")
                        .with_planner_type("none")
                        .with_orchestrator_type("react")
                        .with_specialized_agents()
                        .initialize_agents())).build()
        await agent.evaluate_agent(langsmith_client=ls_client, is_prueba=is_prueba)
        #await agent.evaluate_agent(langsmith_client=ls_client, is_prueba=is_prueba, dataset_name="evaluate_main_agent_memory", dataset_split="test")
    finally:
        await MCPClient.cleanup()
        
async def delete_memory_docs():
    store = (await PostgresPoolManager.get_instance()).get_memory_store()
    await delete_all_memory_documents(store=store)

async def init_double_main_agent() -> DoubleMainAgent:
    builder_simple = FlexibleAgentBuilder()
    builder_simple.with_main_agent_type("orchestrator_only") \
        .with_planner_type("none") \
        .with_orchestrator_type("react") \
        .with_specialized_agents()
    await builder_simple.initialize_agents()
    simple_agent = await builder_simple.build()

    builder_complex = FlexibleAgentBuilder()
    builder_complex.with_main_agent_type("basic") \
        .with_planner_type("orchestrator_planner") \
        .with_orchestrator_type("dummy") \
        .with_specialized_agents()
    await builder_complex.initialize_agents()
    complex_agent = await builder_complex.build()

    classifier_agent = ClassifierAgent(
        use_tuned_model=True
    )

    double_main_agent = DoubleMainAgent(
        classifier_agent=classifier_agent,
        simple_main_agent=simple_agent,
        complex_main_agent=complex_agent
    )
    await double_main_agent.init_memory_store()

    return double_main_agent

async def execute_double_main_agent():
    try:
        double_main_agent = await init_double_main_agent()
        query= "Qué formas de despliegue hay disponibles en el proyecto?"
        result = await double_main_agent.execute_agent_graph_with_exception_handling(
            input={"query": query}
        )
    finally:
        await MCPClient.cleanup()

async def evaluate_double_main_agent():
    try:
        double_main_agent = await init_double_main_agent()
        await double_main_agent.evaluate_agent(langsmith_client=Client(), is_prueba=False)
    finally:
        await MCPClient.cleanup()

async def evaluate_classifier_agent():
    agent = ClassifierAgent(use_tuned_model=True)
    await agent.evaluate_agent(langsmith_client=Client())

async def probar_modelo_hf():
    login(token=os.getenv("HUGGINGFACEHUB_API_TOKEN"))
    model_id = "MartinElMolon/RoBERTa_question_difficulty_classifier"

    classifier = pipeline("text-classification", model=model_id)

    resultado = classifier("Qué metodología de gestión se utiliza?")
    print(resultado)


if __name__ == '__main__':
    load_dotenv()


    #asyncio.run(debug_agent())
    #create_langsmith_datasets(dataset_prueba=False, agents_to_update=["main_agent"])
    #asyncio.run(evaluate_main_agent(is_prueba=False))

    #asyncio.run(evaluate_orchestrator_planner_agent())
    #asyncio.run(evaluate_cached_confluence_agent())

    #asyncio.run(prueba())
    #clase = ClaseB()
    #asyncio.run(clase.prueba())
    #asyncio.run(call_agent())
    
    #asyncio.run(evaluate_main_agent(is_prueba=True))

    #create_main_agent_memory_partitioned_datasets()

    #asyncio.run(delete_memory_docs())
    #create_easy_and_hard_datasets()
    #asyncio.run(prueba())
    #create_question_classifier_dataset()
    #asyncio.run(evaluate_classifier_agent())
    asyncio.run(evaluate_double_main_agent())
    #asyncio.run(probar_modelo_hf())
    #asyncio.run(execute_double_main_agent())
