from typing import List

from langchain_core.messages import BaseMessage, AIMessage
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph
from langsmith import Client

from src.BaseAgent import AgentState, BaseAgent
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
        specialized_agents_responses = result.get("low_level_plan_execution_result")
        if specialized_agents_responses:
            state["messages"].extend([AIMessage(content=message_content) for message_content in specialized_agents_responses])

        return state

    def check_plan_is_finished(self, state: MainAgentState):
        is_finished = False
        plann_response = state.get("planner_high_level_plan")
        if plann_response:
            is_finished = plann_response.finished

        if is_finished:
            return "formatter"
        else:
            return "orchestrator"

    def create_graph(self) -> CompiledGraph:

        graph_builder = StateGraph(MainAgentState)

        # todo: mover esto a BaseAgent
        async def prepare_node(state: MainAgentState) -> MainAgentState:
            print(f"--> Ejecutando agente {self.name}")

            state["planner_current_step"] = 0

            state["messages"] = await self.prepare_prompt(state["query"])
            return state

        planner_graph = self.planner_agent.create_graph()
        formatter_graph = self.formatter_agent.create_graph()

        graph_builder.add_node("prepare", prepare_node)
        graph_builder.add_node("planner", planner_graph)
        graph_builder.add_node("orchestrator", self.execute_orchestrator_graph)
        graph_builder.add_node("formatter", formatter_graph)

        graph_builder.add_conditional_edges("planner", self.check_plan_is_finished)

        graph_builder.set_entry_point("prepare")
        graph_builder.add_edge("prepare", "planner")
        graph_builder.add_edge("orchestrator", "planner")

        return graph_builder.compile()


    async def prepare_prompt(self, query: str) -> List[BaseMessage]:
        return []

    def process_result(self, agent_state: AgentState) -> AIMessage:
        pass

    async def execute_from_dataset(self, inputs: dict) -> dict:
        pass

    async def evaluate_agent(self, langsmith_client: Client):
        pass