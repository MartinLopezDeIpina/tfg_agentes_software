from typing import List

from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.runnables.graph import CurveStyle, NodeStyles, MermaidDrawMethod
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph
from langsmith import Client

from src.BaseAgent import AgentState, BaseAgent
from src.eval_agents.llm_as_judge_evaluator import JudgeLLMEvaluator
from src.formatter_agent.formatter_graph import FormatterAgent
from src.orchestrator_agent.orchestrator_agent_graph import OrchestratorAgent
from src.planner_agent.models import PlannerResponse
from src.planner_agent.planner_agent_graph import PlannerAgent
from src.planner_agent.state import MainAgentState
from src.specialized_agents.SpecializedAgent import SpecializedAgent



class MainAgent(BaseAgent):

    planner_agent: PlannerAgent
    orchestrator_agent: OrchestratorAgent
    formatter_agent: FormatterAgent

    def __init__(
            self,
            planner_agent: PlannerAgent,
            orchestrator_agent: OrchestratorAgent,
            formatter_agent: FormatterAgent,
            debug=True
                 ):

        super().__init__(
            name="main_agent",
            model=None,
            debug=debug
        )
        self.planner_agent = planner_agent
        self.orchestrator_agent = orchestrator_agent
        self.formatter_agent = formatter_agent

    async def execute_orchestrator_graph(self, state: MainAgentState) -> MainAgentState:
        if "planner_high_level_plan" in state:
            next_step = state["planner_high_level_plan"].steps[0]
        else:
            return state

        orchestrator_graph = self.orchestrator_agent.create_graph()
        result = await orchestrator_graph.ainvoke({
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
        formatter_graph = self.formatter_agent.create_graph()

        graph_builder.add_node("prepare", self.prepare_prompt)
        graph_builder.add_node("planner", planner_graph)
        graph_builder.add_node("orchestrator", self.execute_orchestrator_graph)
        graph_builder.add_node("formatter", formatter_graph)

        graph_builder.add_conditional_edges("planner", self.check_plan_is_finished)

        graph_builder.set_entry_point("prepare")
        graph_builder.add_edge("prepare", "planner")
        graph_builder.add_edge("orchestrator", "planner")
        graph_builder.set_finish_point("formatter")

        return graph_builder.compile()


    def process_result(self, agent_state: MainAgentState) -> str:
        return agent_state.get("formatter_result")

    async def evaluate_agent(self, langsmith_client: Client):
        evaluators = [
            JudgeLLMEvaluator()
        ]
        return await self.call_agent_evaluation(langsmith_client, evaluators)