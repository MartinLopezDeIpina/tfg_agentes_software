from abc import ABC, abstractmethod
from typing import List, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ChatMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph
from langsmith import Client

from config import default_reasoner_llm, default_llm
from src.BaseAgent import BaseAgent, AgentState
from src.evaluators.llm_as_judge_evaluator import JudgeLLMEvaluator
from src.orchestrator_agent.orchestrator_agent_graph import OrchestratorAgent
from src.planner_agent.few_shots_examples import planner_few_shots, orchestrator_planner_few_shots
from src.structured_output_validator import execute_structured_llm_with_validator_handling
from src.planner_agent.models import PlannerResponse, BasicPlannerResponse, OrchestratorPlannerResponse, PlanAIMessage
from src.planner_agent.state import MainAgentState
from src.specialized_agents.SpecializedAgent import SpecializedAgent, get_agents_description
from src.utils import tab_all_lines_x_times, print_markdown, get_list_from_string_comma_separated_values
from static.agent_descriptions import PROJECT_DESCRIPTION
from static.prompts import PLANNER_PROMPT_INITIAL, PLANNER_PROMPT_AFTER, SOLVER_AGENT_PROMPT, PLANNER_STRUCURE_PROMPT, \
    ORCHESTRATOR_PLANNER_PROMPT


class PlannerAgent(BaseAgent, ABC):
    max_steps: int
    structure_model: BaseChatModel

    def __init__(
            self,
            planner_model: BaseChatModel = default_reasoner_llm,
            structure_model:BaseChatModel = default_llm,
            max_steps: int = 4,
            debug: bool = True,
    ):
        super().__init__(
            name="planner_agent",
            model=planner_model,
            debug = debug,
        )

        self.structure_model = structure_model
        self.max_steps = max_steps


    def check_current_step(self, state: MainAgentState):
        if state["planner_current_step"] >= self.max_steps:
            state["planner_high_level_plan"].finished = True
            return "finish"
        else:
            return "execute_planner_reasoner"

    def end_plan_execution(self, state: MainAgentState):
        return state

    def format_planner_prompt(self, messages: List[BaseMessage], current_plan: PlannerResponse) -> str:
        initial_message = messages[0].content

        step_result = ""
        for message in messages[1:]:
            if isinstance(message, PlanAIMessage):
                step_result+= "\n-Generated Plan:"
                step_result += f"\n{tab_all_lines_x_times(message.content)}\n"
            else:
                step_result+= "\n-Researcher output:"
                step_result += f"\n{tab_all_lines_x_times(message.content)}\n"

        prompt = PLANNER_PROMPT_AFTER.format(
            initial_prompt=initial_message,
            step_result=step_result,
        )

        return prompt

    async def execute_planner_reasoner_agent(self, state: MainAgentState):
        print("+Ejecutando agente planner")
        messages = state["messages"]
        if len(messages) == 1:
            # si es el primer plan que se hace
            planner_input = messages[0].content
        else:
            planner_input = self.format_planner_prompt(messages, state["planner_high_level_plan"])

        planner_scratchpad = await self.model.ainvoke(
            input=planner_input
        )

        await self.stream_manager.emit_planner_activity(
            plan_content=planner_scratchpad.content,
            activity_description="plan de orquestación completado"
        )

        state["planner_scratchpad"] = planner_scratchpad.content

        state["planner_current_step"] += 1
        return state

    @abstractmethod
    def execute_planner_structure_agent(self, state: MainAgentState):
        """
        El paso del agente planificador enfocado en generar el plan desde el razonamiento del plan
        Intentar estructurar la salida del planner con el validador.
        Si no se consigue después de varios intentos devolver el plan completo en el siguiente paso.
        """

    def create_graph(self) -> CompiledGraph:
        """
        Devolver el grafo compilado del agente
        Si se llega al máximo de iteraciones, el nodo condicional check_and_increment_current_step devolverá directamente el finish sin ejecutar el planner.
        """
        graph_builder = StateGraph(MainAgentState)

        graph_builder.add_node("prepare", self.prepare_prompt)
        graph_builder.add_node("execute_planner_reasoner", self.execute_planner_reasoner_agent)
        graph_builder.add_node("execute_planner_structure", self.execute_planner_structure_agent)
        graph_builder.add_node("finish", self.end_plan_execution)

        graph_builder.add_conditional_edges("prepare", self.check_current_step)

        graph_builder.set_entry_point("prepare")
        graph_builder.add_edge("execute_planner_reasoner", "execute_planner_structure")
        graph_builder.add_edge("execute_planner_structure", "finish")

        return graph_builder.compile()

    def process_result(self, agent_state: MainAgentState) -> str:
        return agent_state.get("planner_high_level_plan").model_dump_json()

    async def evaluate_agent(self, langsmith_client: Client):
        evaluators=[
            JudgeLLMEvaluator()
        ]
        result = await self.call_agent_evaluation(langsmith_client, evaluators)
        return result

    async def execute_from_dataset(self, inputs: dict) -> dict:
        """
        Si no hay mensajes en el dataset entonces es la primera iteración en el plan.
        Si hay mensajes nuevos preparar el estado con estos para ejecutar el paso a evaluar.
        """
        try:
            messages_str = inputs.get("messages")
            messages = []
            if messages_str:
                # Incluir el mensaje del sistema en caso de no ser la primera vez que se ejecuta el plan
                system_message = self.prepare_prompt({"query": inputs.get("query"), "messages": []})["messages"][0]
                messages.append(system_message)
                messages.extend([AIMessage(content=message) for message in get_list_from_string_comma_separated_values(messages_str)])

            current_plan_str = inputs.get("current_plan")
            current_high_level_plan = None
            if current_plan_str:
                current_plan_list = get_list_from_string_comma_separated_values(current_plan_str)
                current_high_level_plan = BasicPlannerResponse(
                    finished=False,
                    plan_reasoning=current_plan_list[0],
                    steps=current_plan_list[1:],
                )
                messages.insert(1,
                    PlanAIMessage(
                        message=AIMessage(
                            content=current_high_level_plan.to_string()
                        )
                    )
                )

            run_state = await self.create_graph().ainvoke({
                "query": inputs["query"],
                "messages": messages,
                "planner_high_level_plan": current_high_level_plan,
                "planner_current_step": 0
            })
            result = self.process_result(run_state)

            return {
                "run_state": run_state,
                "result": result
            }
        except Exception as e:
            return{
                "error": True
            }

class BasicPlannerAgent(PlannerAgent):

    def __init__(self,
        planner_model: BaseChatModel = default_reasoner_llm,
        structure_model:BaseChatModel = default_llm,
        max_steps: int = 4,
        debug: bool = True
                 ):
        super().__init__(
            planner_model=planner_model,
            structure_model=structure_model,
            max_steps=max_steps,
            debug=debug
        )

    async def execute_planner_structure_agent(self, state: MainAgentState) -> MainAgentState:
        planner_scratchpad = state.get("planner_scratchpad")
        try:
            prompt=PLANNER_STRUCURE_PROMPT.format(plan=planner_scratchpad)
            planner_result = await execute_structured_llm_with_validator_handling(
                prompt=prompt,
                llm=self.structure_model,
                output_schema=BasicPlannerResponse,
            )

            state["planner_high_level_plan"] = planner_result
            state["messages"].append(PlanAIMessage(
                message=AIMessage(
                    content=planner_result.to_string()
                )
            ))

        except Exception as e:
            state["planner_high_level_plan"] = BasicPlannerResponse(
                plan_reasoning=planner_scratchpad,
                steps=[planner_scratchpad],
                finished=False
            )
        finally:
            return state

    def prepare_prompt(self, state: MainAgentState) -> MainAgentState:
        messages = state["messages"]
        if not messages or len(messages) == 0:
            state["messages"] = [
                SystemMessage(
                    content=PLANNER_PROMPT_INITIAL.format(
                        proyect_context=PROJECT_DESCRIPTION,
                        user_query=state["query"],
                        few_shot_examples=planner_few_shots
                    )
                ),
            ]
        return state


class OrchestratorPlannerAgent(PlannerAgent):

    available_agents_description: str

    def __init__(self,
                 planner_model: BaseChatModel = default_reasoner_llm,
                 structure_model:BaseChatModel = default_llm,
                 max_steps: int = 4,
                 debug: bool = True,
                 available_agents: List[SpecializedAgent] = None
                 ):
        super().__init__(
            planner_model=planner_model,
            structure_model=structure_model,
            max_steps=max_steps,
            debug=debug
        )
        self.available_agents_description = get_agents_description(available_agents)

    def prepare_prompt(self, state: AgentState) -> AgentState:
        messages = state["messages"]
        if not messages or len(messages) == 0:
            state["messages"] = [
                SystemMessage(
                    content=ORCHESTRATOR_PLANNER_PROMPT.format(
                        project_description=PROJECT_DESCRIPTION,
                        user_query=state["query"],
                        available_agents=self.available_agents_description,
                        few_shot_examples=orchestrator_planner_few_shots
                    )
                ),
            ]
        return state

    async def execute_planner_structure_agent(self, state: MainAgentState):
        planner_scratchpad = state.get("planner_scratchpad")
        try:
            prompt=PLANNER_STRUCURE_PROMPT.format(plan=planner_scratchpad)
            planner_result = await execute_structured_llm_with_validator_handling(
                prompt=prompt,
                llm=self.structure_model,
                output_schema=OrchestratorPlannerResponse,
            )

            state["planner_high_level_plan"] = planner_result
            state["messages"].append(PlanAIMessage(
                message=AIMessage(
                    content=planner_result.to_string()
                )
            ))

        except Exception as e:
            state["planner_high_level_plan"] = BasicPlannerResponse(
                plan_reasoning=planner_scratchpad,
                steps=[planner_scratchpad],
                finished=False
            )
        finally:
            return state
