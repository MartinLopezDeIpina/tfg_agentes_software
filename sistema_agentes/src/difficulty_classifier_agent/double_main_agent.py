from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langchain_core.stores import BaseStore
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph
from langsmith import Client

from config import default_llm
from src.BaseAgent import AgentState, BaseAgent
from src.db.postgres_connection_manager import PostgresPoolManager
from src.difficulty_classifier_agent.difficulty_classifier_graph import ClassifierAgent, ClassifierAgentState
from src.evaluators.cite_references_evaluator import CiteEvaluator
from src.evaluators.llm_as_judge_evaluator import JudgeLLMEvaluator
from src.evaluators.question_difficulty_evaluator import QuestionDifficultyEvaluator
from src.difficulty_classifier_agent.few_shots import classifier_few_shots
from src.difficulty_classifier_agent.models import ClassifierResponse
from src.main_agent.main_graph import MainAgent
from src.planner_agent.state import MainAgentState
from src.specialized_agents.citations_tool.models import CitedAIMessage
from src.structured_output_validator import execute_structured_llm_with_validator_handling
from src.utils import normalize_agent_input_for_reasoner_agent
from static.prompts import CLASSIFIER_AGENT_PROMPT


class DoubleMainAgentState(MainAgentState):
    classifier_result: ClassifierResponse
    main_final_state: MainAgentState

class DoubleMainAgent(BaseAgent):
    simple_main_agent: MainAgent
    complex_main_agent: MainAgent
    classifier_agent: ClassifierAgent
    memory_store: BaseStore

    def __init__(self,
                 simple_main_agent: MainAgent,
                 complex_main_agent: MainAgent,
                 classifier_agent: ClassifierAgent,
                 model: BaseChatModel = default_llm,
                 prompt: str = "",
                 ):

        self.simple_main_agent = simple_main_agent
        self.complex_main_agent = complex_main_agent
        self.classifier_agent = classifier_agent

        super().__init__(
            name="classifier_agent",
            model = model,
            debug=True,
            prompt = prompt
        )

    async def prepare_prompt(self, state, store):
        pass


    def process_result(self, state: DoubleMainAgentState) -> CitedAIMessage:
        # Access formatter_result directly from the state
        return state.get("formatter_result")

    async def execute_main_agent(self, state: DoubleMainAgentState) -> DoubleMainAgentState:
        difficulty = state.get("classifier_result")
        
        # Prepare complete input for inner agents
        agent_input = {
            "query": state.get("query"),
            "messages": state.get("messages", [])
        }
        
        if difficulty.difficulty == "HARD":
            main_final_state = await self.complex_main_agent.execute_agent_graph_with_exception_handling(
                input=agent_input
            )
        else:
            main_final_state = await self.simple_main_agent.execute_agent_graph_with_exception_handling(
                input=agent_input
            )
        
        print(f"Pregunta es {difficulty.difficulty}")
        
        # Copy the result directly to our state
        state.update(main_final_state)
        return state

    async def execute_classifier(self, state: DoubleMainAgentState) -> DoubleMainAgentState:
        classifier_input = {
            "query": state.get("query"),
            "messages": []
        }
        
        classifier_result = await self.classifier_agent.execute_agent_graph_with_exception_handling(
            input=classifier_input
        )
        
        state["classifier_result"] = ClassifierAgent.process_result(classifier_result)
        return state

    async def init_memory_store(self):
        # Inicializar el store para el agente principal
        postgre = await PostgresPoolManager().get_instance()
        store = postgre.get_memory_store()
        self.memory_store = store

        # Asegurarse de que los agentes internos tengan el mismo store
        self.simple_main_agent.memory_store = store
        self.complex_main_agent.memory_store = store

    def create_graph(self) -> CompiledGraph:
        graph_builder = StateGraph(DoubleMainAgentState)

        graph_builder.add_node("classifier_agent", self.execute_classifier)
        graph_builder.add_node("main_agent", self.execute_main_agent)

        graph_builder.set_entry_point("classifier_agent")
        graph_builder.add_edge("classifier_agent", "main_agent")

        return graph_builder.compile(store=self.memory_store)

    async def evaluate_agent(self, langsmith_client: Client, is_prueba: bool = True, dataset_name: str = None, dataset_split: str = None):
        evaluators = [
            JudgeLLMEvaluator()
        ]
        return await self.call_agent_evaluation(langsmith_client=langsmith_client, evaluators=evaluators, is_prueba=is_prueba, dataset_name=dataset_name or "evaluate_main_agent_prueba" if is_prueba else "evaluate_main_agent" , dataset_split=dataset_split)
