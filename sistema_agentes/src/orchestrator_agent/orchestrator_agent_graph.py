import asyncio
from typing import TypedDict, List

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph
from langsmith import Client

from src.BaseAgent import BaseAgent, AgentState
from src.eval_agents.llm_as_judge_evaluator import JudgeLLMEvaluator
from src.eval_agents.tool_precision_evaluator import ToolPrecisionEvaluator
from src.orchestrator_agent.models import OrchestratorPlan, AgentStep
from src.specialized_agents.SpecializedAgent import SpecializedAgent
from static.prompts import ORCHESTRATOR_PROMPT

class OrchestratorAgentState(AgentState):
    planner_high_level_plan: str
    orchestrator_low_level_plan: OrchestratorPlan
    low_level_plan_execution_result: List[AIMessage]

class OrchestratorAgent(BaseAgent):

    available_agents: List[SpecializedAgent]

    def __init__(
            self,
            available_agents: List[SpecializedAgent],
            model: BaseChatModel = None,
            debug: bool = True
                 ):
        super().__init__(
            name="orchestrator_agent",
            model=model,
            debug=debug
        )
        self.available_agents = available_agents

    async def prepare_prompt(self, state: OrchestratorAgentState) -> OrchestratorAgentState:
        agents_description = ""
        for agent in self.available_agents:
            agents_description += f"\n-{agent.to_string()}"

        state["messages"] = [
            SystemMessage(
                content=ORCHESTRATOR_PROMPT.format(
                    available_agents=agents_description
                )
            ),
            HumanMessage(
                content=state["planner_high_level_plan"]
            )
        ]
        return state

    async def execute_orchestrator_agent(self, state: OrchestratorAgentState) -> OrchestratorAgentState:
        print("+Ejecutando agente orquestador")

        structured_llm = BaseChatModel.with_structured_output(self.model, schema=OrchestratorPlan)

        try:
            orchestrator_result = await structured_llm.ainvoke(
                input=state["messages"]
            )
            if not isinstance(orchestrator_result, OrchestratorPlan):
                orchestrator_result = OrchestratorPlan.model_validate(orchestrator_result)

            state["orchestrator_low_level_plan"] = orchestrator_result

        except Exception as e:
            print(f"Error en structured output: {e}")
            #todo: gestionar parsing

        finally:
            return state

    async def execute_agents(self, state: OrchestratorAgentState) -> OrchestratorAgentState:
        orchestrator_plan = state.get("orchestrator_low_level_plan")
        if orchestrator_plan is None:
            return state

        # Agrupar por cada agente un task para ejecutar de forma asíncrona
        executed_steps = []
        for step in orchestrator_plan.steps_to_complete:
            agent_name = step.agent_name
            step_agent = None
            for agent in self.available_agents:
                if agent.name == agent_name:
                    step_agent = agent
            if step_agent:
                agent_graph = step_agent.create_graph()
                task = agent_graph.ainvoke({
                    "query":step.query,
                    "messages": []
                })
                executed_steps.append({
                    "task": task,
                    "step": step,
                    "agent": step_agent
                })

        if len(executed_steps) > 0:
            agent_tasks = [task["task"] for task in executed_steps]
            agent_states = await asyncio.gather(*agent_tasks)
        else:
            return state

        state["low_level_plan_execution_result"] = []
        for i, agent_final_state in enumerate(agent_states):
            result = executed_steps[i]["agent"].process_result(agent_final_state)
            state["low_level_plan_execution_result"].append(result)

        return state

    def create_graph(self) -> CompiledGraph:
        """
        Devolver el grafo compilado del agente
        """
        graph_builder = StateGraph(OrchestratorAgentState)

        graph_builder.add_node("prepare", self.prepare_prompt)
        graph_builder.add_node("execute_orchestrator", self.execute_orchestrator_agent)
        graph_builder.add_node("execute_agents", self.execute_agents)

        graph_builder.set_entry_point("prepare")
        graph_builder.add_edge("prepare", "execute_orchestrator")
        graph_builder.add_edge("execute_orchestrator", "execute_agents")
        graph_builder.set_finish_point("execute_agents")

        return graph_builder.compile()

    def process_result(self, agent_state: OrchestratorAgentState) -> List[AIMessage]:
        specialized_agents_responses = agent_state.get("low_level_plan_execution_result")
        return specialized_agents_responses

    async def execute_from_dataset(self, inputs: dict) -> dict:
        """
        Para evaluar el agente orquestador solo ejecutar el agente encargado de decidir
        cuáles agentes especializados elegir, no ejecutar los especializados.
        """
        try:
            state = OrchestratorAgentState(
                planner_high_level_plan=inputs["query"],
            )
            state = await self.prepare_prompt(state)
            run_state = await self.execute_orchestrator_agent(state)

            result = ""
            for agent_step in run_state["orchestrator_low_level_plan"].steps_to_complete:
                result += f"{agent_step.agent_name}: {agent_step.query}\n\n"

            return {
                "run_state": run_state,
                "result": result
            }
        except Exception as e:
            return {
                "error": True
            }

    @staticmethod
    def get_tools_from_run_state(state: OrchestratorAgentState) -> List[str]:
        tools = []
        orchestrator_response = state["orchestrator_low_level_plan"]
        for agent_step in orchestrator_response.steps_to_complete:
            tools.append(agent_step.agent_name.value)
        return tools

    async def evaluate_agent(self, langsmith_client: Client):
        evaluators = [
            ToolPrecisionEvaluator(self.get_tools_from_run_state),
            JudgeLLMEvaluator()
        ]

        result = await self.call_agent_evaluation(langsmith_client, evaluators)
        return result





