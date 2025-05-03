import asyncio
import json

from langgraph.prebuilt import create_react_agent
from abc import ABC, abstractmethod
from typing import TypedDict, List

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolCall, ToolMessage
from langchain_core.tools import BaseTool, tool
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph
from langsmith import Client

from config import default_llm
from src.BaseAgent import BaseAgent, AgentState
from src.evaluators.tool_precision_evaluator import ToolPrecisionEvaluator
from src.orchestrator_agent.few_shots_examples import orchestrator_few_shots
from src.orchestrator_agent.models import OrchestratorPlan, AgentStep
from src.structured_output_validator import execute_structured_llm_with_validator_handling
from src.specialized_agents.SpecializedAgent import SpecializedAgent, get_agents_description
from src.specialized_agents.citations_tool.models import CitedAIMessage
from static.agent_descriptions import PROJECT_DESCRIPTION
from static.prompts import ORCHESTRATOR_PROMPT, REACT_ORCHESTRATOR_PROMPT


class OrchestratorAgentState(AgentState):
    # El high level plan representa lo que el orquestador tiene que responder, puede ser un paso de un plan o directamente una pregunta del usuario.
    planner_high_level_plan: str | OrchestratorPlan
    orchestrator_low_level_plan: OrchestratorPlan
    low_level_plan_execution_result: List[CitedAIMessage]

class OrchestratorAgent(BaseAgent, ABC):

    available_agents: List[SpecializedAgent]

    def __init__(
            self,
            available_agents: List[SpecializedAgent],
            model: BaseChatModel = default_llm,
            debug: bool = True
                 ):
        super().__init__(
            name="orchestrator_agent",
            model=model,
            debug=debug
        )
        self.available_agents = available_agents

    @abstractmethod
    def create_orchestrate_agents_graph(self, state: OrchestratorAgentState) -> CompiledGraph:
        """
        Define la lógica de ejecución del orquestador, debe ejecutar los agentes especializados
        """

    def create_graph(self) -> CompiledGraph:
        """
        Devolver el grafo compilado del agente
        """
        graph_builder = StateGraph(OrchestratorAgentState)

        orchestrate_agents_graph = self.create_orchestrate_agents_graph

        graph_builder.add_node("prepare", self.prepare_prompt)
        graph_builder.add_node("orchestrator", orchestrate_agents_graph)


        graph_builder.set_entry_point("prepare")
        graph_builder.add_edge("prepare", "orchestrator")

        return graph_builder.compile()

    def process_result(self, agent_state: OrchestratorAgentState) -> List[CitedAIMessage]:
        specialized_agents_responses = agent_state.get("low_level_plan_execution_result")
        return specialized_agents_responses

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
        ]

        result = await self.call_agent_evaluation(langsmith_client, evaluators)
        return result


class OneStepOrchestratorAgent(OrchestratorAgent, ABC):
    """
    Ejecuta una única iteración de uno o varios agentes asíncronos especializados.
    """

    def __init__(
            self,
            available_agents: List[SpecializedAgent],
            model: BaseChatModel = default_llm,
            debug: bool = True
    ):
        super().__init__(
            available_agents=available_agents,
            model=model,
            debug=debug
        )

    @abstractmethod
    async def execute_orchestrator_agent(self, state: OrchestratorAgentState) -> OrchestratorAgentState:
        """
        Define la lógica de ejecución del agente orquestador, desde un plan a alto nivel genera un plan a bajo nivel (los agentes especializados a llamar)
        """

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
                task = step_agent.execute_agent_graph_with_exception_handling({
                    "query":step.query,
                    "messages": [],
                    "remaining_steps": 1
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

    def create_orchestrate_agents_graph(self, state: OrchestratorAgentState) -> CompiledGraph:
        """
        Dada una query ejecuta los agentes especializados y obtiene los mensajes citados
        """

        graph_builder = StateGraph(OrchestratorAgentState)

        graph_builder.add_node("execute_orchestrator", self.execute_orchestrator_agent)
        graph_builder.add_node("execute_agents", self.execute_agents)

        graph_builder.set_entry_point("execute_orchestrator")
        graph_builder.add_edge("execute_orchestrator", "execute_agents")

        return graph_builder.compile()


class BasicOrchestratorAgent(OneStepOrchestratorAgent):

    def __init__(self,
        available_agents: List[SpecializedAgent],
        model: BaseChatModel = default_llm,
        debug: bool = True
    ):
        super().__init__(
            available_agents=available_agents,
            model=model,
            debug=debug
        )

    async def execute_from_dataset(self, inputs: dict) -> dict:
        """
        Para evaluar el agente orquestador solo ejecutar el agente encargado de decidir
        cuáles agentes especializados elegir, no ejecutar los especializados.
        """
        try:
            state = OrchestratorAgentState(
                planner_high_level_plan=inputs["current_plan"],
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

    async def prepare_prompt(self, state: OrchestratorAgentState) -> OrchestratorAgentState:
        agents_description = get_agents_description(self.available_agents)

        messages = state.get("messages")
        if not messages:
            state["messages"] = []

        state["messages"].insert(0,
                                 SystemMessage(
                                     content=ORCHESTRATOR_PROMPT.format(
                                         available_agents=agents_description,
                                         few_shots_examples=orchestrator_few_shots
                                     )
                                 ),
                                 )
        state["messages"].append(
            HumanMessage(
                content=state["planner_high_level_plan"]
            )
        )
        return state

    async def execute_orchestrator_agent(self, state: OrchestratorAgentState) -> OrchestratorAgentState:
        """
        Intenta ejecutar el orquestador con varios intentos de parsing.
        Si falla tras varios intentos crea un plan si pasos.
        """
        print("+Ejecutando agente orquestador")
        try:
            prompt = state["messages"]
            orchestrator_result = await execute_structured_llm_with_validator_handling(
                prompt=prompt,
                output_schema=OrchestratorPlan,
                llm=self.model
            )

            if not isinstance(orchestrator_result, OrchestratorPlan):
                orchestrator_result = OrchestratorPlan.model_validate(orchestrator_result)

            state["orchestrator_low_level_plan"] = orchestrator_result

        except Exception as e:
            print(f"Error en structured output: {e}")
            state["orchestrator_low_level_plan"] = OrchestratorPlan(
                steps_to_complete=[]
            )
        finally:
            return state

class DummyOrchestratorAgent(OneStepOrchestratorAgent):

    def __init__(self,
                 available_agents: List[SpecializedAgent],
                 debug: bool = True
                 ):
        super().__init__(
            available_agents=available_agents,
            debug=debug
        )

    async def execute_orchestrator_agent(self, state: OrchestratorAgentState) -> OrchestratorAgentState:
        """
        Simplemente traduce el plan de los agentes a ejecutar desde el plan ya creado del PlannerOrchestrator
        """
        state["orchestrator_low_level_plan"] = state.get("planner_high_level_plan")

        return state

    async def prepare_prompt(self, state: OrchestratorAgentState) -> AgentState:
        return state

class ReactOrchestratorAgent(OrchestratorAgent):

    agent_tools: List[BaseTool]

    def __init__(self,
                 available_agents: List[SpecializedAgent],
                 debug: bool = True
                 ):
        super().__init__(
            available_agents=available_agents,
            debug=debug
        )

        self.agent_tools = []
        for agent in available_agents:
            self.agent_tools.append(self.transform_specialized_agent_into_tool(agent))

    async def prepare_prompt(self, state: OrchestratorAgentState) -> AgentState:
        agents_description = get_agents_description(self.available_agents)
        state["messages"] = []

        state["messages"].extend([
            SystemMessage(
                content=REACT_ORCHESTRATOR_PROMPT.format(
                    project_description=PROJECT_DESCRIPTION
                )
            ),
            HumanMessage(
                content=state["planner_high_level_plan"]
            )
        ])

        return state


    def transform_specialized_agent_into_tool(self, agent: SpecializedAgent) -> BaseTool:
        @tool
        async def call_agent(query: str):
            """
            Esta docstring será sustituida por la descripción del agente
            """
            result_state = await agent.execute_agent_graph_with_exception_handling(
                input={
                    "query": query,
                    "messages": []
                }
            )
            cited_ai_message = agent.process_result(result_state)
        
            return cited_ai_message.to_dict()
        call_agent.__doc__ = agent.description
        
        return call_agent

    def parse_results(selfs, state: OrchestratorAgentState) -> OrchestratorAgentState:
        messages = state.get("messages")
        if not messages:
            return state

        cited_ai_messages = []
        for message in messages:
            if isinstance(message, ToolMessage):
                cited_message = CitedAIMessage.from_string(string=message.content)
                if cited_message:
                    cited_ai_messages.append(cited_message)

        state["low_level_plan_execution_result"] = cited_ai_messages
        return state



    def create_orchestrate_agents_graph(self, state: OrchestratorAgentState) -> CompiledGraph:

        graph_builder = StateGraph(OrchestratorAgentState)

        react_graph = create_react_agent(
            tools=self.agent_tools,
            model=self.model
        )

        graph_builder.add_node("react_agent", react_graph)
        graph_builder.add_node("parse_results", self.parse_results)

        graph_builder.set_entry_point("react_agent")
        graph_builder.add_edge("react_agent", "parse_results")

        return graph_builder.compile()





