from abc import ABC
from typing import List

from langchain.chains.question_answering.map_reduce_prompt import messages
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.runnables.graph import CurveStyle, NodeStyles, MermaidDrawMethod
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph
from langsmith import Client

from src.BaseAgent import AgentState, BaseAgent
from src.evaluators.cite_references_evaluator import CiteEvaluator
from src.evaluators.llm_as_judge_evaluator import JudgeLLMEvaluator
from src.formatter_agent.formatter_graph import FormatterAgent
from src.orchestrator_agent.orchestrator_agent_graph import OrchestratorAgent
from src.planner_agent.models import PlannerResponse
from src.planner_agent.planner_agent_graph import PlannerAgent
from src.planner_agent.state import MainAgentState
from src.specialized_agents.SpecializedAgent import SpecializedAgent
from src.specialized_agents.citations_tool.models import CitedAIMessage


class MainAgent(BaseAgent, ABC):

    formatter_agent: FormatterAgent

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

    async def evaluate_agent(self, langsmith_client: Client, is_prueba: bool = False):
        evaluators = [
            JudgeLLMEvaluator(),
            CiteEvaluator()
        ]
        return await self.call_agent_evaluation(langsmith_client=langsmith_client, evaluators=evaluators, is_prueba=is_prueba)

class BasicMainAgent(MainAgent):

    planner_agent: PlannerAgent
    orchestrator_agent: OrchestratorAgent
    formatter_agent: FormatterAgent

    def __init__(self,
                 planner_agent: PlannerAgent,
                 orchestrator_agent: OrchestratorAgent,
                 formatter_agent: FormatterAgent
                 ):
        super().__init__(
            formatter_agent = formatter_agent
        )
        self.planner_agent = planner_agent
        self.orchestrator_agent = orchestrator_agent


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

        return graph_builder.compile()

"""
class OrchestratorPlannerTogetherMainAgent(MainAgent):
    def __init__(self,
             debug=True
                 ):
        super().__init__(
        )
"""

