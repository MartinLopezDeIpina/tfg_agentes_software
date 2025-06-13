from abc import ABC
from typing import List, Union

from langchain.chains.question_answering.map_reduce_prompt import messages
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from langchain_core.runnables.graph import CurveStyle, NodeStyles, MermaidDrawMethod
from langchain_core.stores import BaseStore
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph
from langsmith import Client

from src.BaseAgent import AgentState, BaseAgent
from src.db.postgres_connection_manager import PostgresPoolManager
from src.evaluators.cite_references_evaluator import CiteEvaluator
from src.evaluators.llm_as_judge_evaluator import JudgeLLMEvaluator
from src.formatter_agent.formatter_graph import FormatterAgent
from src.orchestrator_agent.orchestrator_agent_graph import OrchestratorAgent
from src.planner_agent.models import PlannerResponse
from src.planner_agent.planner_agent_graph import PlannerAgent
from src.planner_agent.state import MainAgentState
from src.specialized_agents.SpecializedAgent import SpecializedAgent
from src.specialized_agents.citations_tool.models import CitedAIMessage
from src.utils import (
    normalize_agent_input_for_reasoner_agent, normalize_agent_input_for_orchestrator_agent,
)


class MainAgent(BaseAgent, ABC):

    orchestrator_agent: OrchestratorAgent
    formatter_agent: FormatterAgent
    memory_store: BaseStore

    def __init__(
            self,
            debug=True,
            formatter_agent: FormatterAgent = None,
                 ):

        super().__init__(
            name="main_agent",
            model=None,
            debug=debug
        )
        self.formatter_agent = formatter_agent or FormatterAgent()

    async def execute_formatter_graph(self, state: MainAgentState):
        messages = state.get("messages")
        query = state.get("query")
        result = await self.formatter_agent.execute_agent_graph_with_exception_handling({
            "query": query,
            "messages": messages
        })
        formatter_result = self.formatter_agent.process_result(result)
        state["formatter_result"] = formatter_result
        return state

    def process_result(self, agent_state: MainAgentState) -> CitedAIMessage:
        return agent_state.get("formatter_result")

    async def evaluate_agent(self, langsmith_client: Client, is_prueba: bool = False, dataset_name: str = None, dataset_split: str = None):
        evaluators = [
            JudgeLLMEvaluator(),
            CiteEvaluator()
        ]
        return await self.call_agent_evaluation(langsmith_client=langsmith_client, evaluators=evaluators, is_prueba=is_prueba, dataset_name=dataset_name, dataset_split=dataset_split)

    async def init_memory_store(self):
        postgre = await PostgresPoolManager().get_instance()
        store = postgre.get_memory_store()
        self.memory_store = store

class BasicMainAgent(MainAgent):

    planner_agent: PlannerAgent

    def __init__(self,
                 planner_agent: PlannerAgent,
                 orchestrator_agent: OrchestratorAgent,
                 formatter_agent: FormatterAgent,
                 ):
        super().__init__(
            formatter_agent = formatter_agent
        )
        self.planner_agent = planner_agent
        self.orchestrator_agent = orchestrator_agent

    async def execute_agent_graph_with_exception_handling(self, input: dict):
        """Override to handle multiple input formats and convert conversation history."""
        normalized_input = normalize_agent_input_for_reasoner_agent(input)
        return await super().execute_agent_graph_with_exception_handling(normalized_input)

    async def execute_orchestrator_graph(self, state: MainAgentState) -> MainAgentState:
        if "planner_high_level_plan" in state:
            next_step = state["planner_high_level_plan"].steps[0]
        else:
            return state

        result = await self.orchestrator_agent.execute_agent_graph_with_exception_handling({
            "planner_high_level_plan":next_step,
        })
        specialized_agents_responses = self.orchestrator_agent.process_result(result)
        if specialized_agents_responses:
            state["messages"].extend(specialized_agents_responses)

        return state

    def check_plan_is_finished(self, state: MainAgentState):
        is_finished = False
        plann_response = state.get("planner_high_level_plan")
        if plann_response:
            is_finished = plann_response.finished

        if is_finished:
            return "formatter"

        return "orchestrator"

    async def prepare_prompt(self, state: MainAgentState) -> MainAgentState:

        print(f"--> Ejecutando agente {self.name}")

        state["planner_current_step"] = 0
        state["messages"] = []

        return state

    def create_graph(self) -> CompiledGraph:

        graph_builder = StateGraph(MainAgentState)

        planner_graph = self.planner_agent.create_graph()

        graph_builder.add_node("prepare", self.prepare_prompt)
        graph_builder.add_node("planner", planner_graph)
        graph_builder.add_node("orchestrator", self.execute_orchestrator_graph)
        graph_builder.add_node("formatter", self.execute_formatter_graph)

        graph_builder.add_conditional_edges("planner", self.check_plan_is_finished)

        graph_builder.set_entry_point("prepare")
        graph_builder.add_edge("prepare", "planner")
        graph_builder.add_edge("orchestrator", "planner")
        
        return graph_builder.compile(store=self.memory_store)

class OrchestratorOnlyMainAgent(MainAgent):
    def __init__(self,
                 orchestrator_agent: OrchestratorAgent,
                 formatter_agent: FormatterAgent,
                 debug: bool = True
                 ):
        super().__init__(
            formatter_agent=formatter_agent,
            debug=debug
        )
        self.orchestrator_agent = orchestrator_agent

    async def execute_agent_graph_with_exception_handling(self, input: dict):
        """Override to handle multiple input formats and convert conversation history."""
        normalized_input = normalize_agent_input_for_orchestrator_agent(input)
        return await super().execute_agent_graph_with_exception_handling(normalized_input)

    async def execute_orchestrator_direct(self, state: MainAgentState) -> MainAgentState:
        result = await self.orchestrator_agent.execute_agent_graph_with_exception_handling({
            "planner_high_level_plan": state["query"],
            "messages": state["messages"]
        })
        specialized_agents_responses = self.orchestrator_agent.process_result(result)
        if specialized_agents_responses:
            state["messages"].extend(specialized_agents_responses)

        return state

    async def prepare_prompt(self, state: MainAgentState) -> MainAgentState:
        print(f"--> Ejecutando agente {self.name} (sin planificador)")
        return state

    def create_graph(self) -> CompiledGraph:
        graph_builder = StateGraph(MainAgentState)

        graph_builder.add_node("prepare", self.prepare_prompt)
        graph_builder.add_node("orchestrator", self.execute_orchestrator_direct)
        graph_builder.add_node("formatter", self.execute_formatter_graph)

        graph_builder.set_entry_point("prepare")
        graph_builder.add_edge("prepare", "orchestrator")
        graph_builder.add_edge("orchestrator", "formatter")

        return graph_builder.compile(store=self.memory_store)

