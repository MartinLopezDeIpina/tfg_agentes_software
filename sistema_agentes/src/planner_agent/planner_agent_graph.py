from typing import List, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ChatMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph
from langsmith import Client

from src.BaseAgent import BaseAgent, AgentState
from src.orchestrator_agent.orchestrator_agent_graph import OrchestratorAgent
from src.planner_agent.models import PlannerResponse
from src.planner_agent.state import MainAgentState
from src.specialized_agents.SpecializedAgent import SpecializedAgent
from src.utils import tab_all_lines_x_times, print_markdown
from static.prompts import PLANNER_PROMPT_INITIAL, PLANNER_PROMPT_AFTER, SOLVER_AGENT_PROMPT, PLANNER_STRUCURE_PROMPT


class PlannerAgent(BaseAgent):
    max_steps: int
    structure_model: BaseChatModel

    def __init__(
            self,
            planner_model: BaseChatModel = ChatOpenAI(model="o3-mini"),
            structure_model:BaseChatModel = ChatOpenAI(model="gpt-4o-mini"),
            max_steps: int = 2,
            debug: bool = True
    ):
        super().__init__(
            name="planner_agent",
            model=planner_model,
            debug = debug
        )

        self.structure_model = structure_model
        self.max_steps = max_steps

    def prepare_prompt(self, state: MainAgentState) -> MainAgentState:
        messages = state["messages"]
        if not messages or len(messages) == 0:
            project_description = "Descripción de proyecto IA-core-tools, un proyecto para crear herramientas para agentes LLM con LangChain, PGVector y Flask"

            state["messages"] = [
                SystemMessage(
                    content=PLANNER_PROMPT_INITIAL.format(
                        proyect_context=project_description,
                        user_query=state["query"],
                    )
                ),
            ]
        return state

    def format_planner_prompt(self, messages: List[BaseMessage], current_plan: PlannerResponse) -> str:
        initial_message = messages[0].content
        planner_current_plan = current_plan.to_string()

        step_result = ""
        for message in messages[1:]:
            step_result+= "\n-Researcher output:"
            step_result += f"\n{tab_all_lines_x_times(message.content)}\n"

        prompt = PLANNER_PROMPT_AFTER.format(
            initial_prompt=initial_message,
            previous_plan=planner_current_plan,
            step_result=step_result,
        )

        return prompt

    async def execute_planner_reasoner_agent(self, state: MainAgentState) -> MainAgentState:
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

        state["planner_scratchpad"] = planner_scratchpad.content


        state["planner_current_step"] += 1
        return state

    def check_current_step(self, state: MainAgentState):
        if state["planner_current_step"] >= self.max_steps:
            state["planner_high_level_plan"].finished = True
            return "finish"
        else:
            return "execute_planner_reasoner"

    def end_plan_execution(self, state: MainAgentState):
        return state

    async def execute_planner_structure_agent(self, state: MainAgentState) -> MainAgentState:
        structured_llm = self.structure_model.with_structured_output(PlannerResponse)
        try:
            planner_result = await structured_llm.ainvoke(
                input=PLANNER_STRUCURE_PROMPT.format(
                    plan=state["planner_scratchpad"]
                )
            )
            if not isinstance(planner_result, PlannerResponse):
                planner_result = PlannerResponse.model_validate(planner_result)

            state["planner_high_level_plan"] = planner_result
            state["messages"].append(AIMessage(
                content=planner_result.to_string()
            ))

        except Exception as e:
            print(f"Error en structured output: {e}")
            #todo: gestionar parsing

        finally:

            return state


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


    def process_result(self, agent_state: AgentState) -> AIMessage:
        pass

    async def execute_from_dataset(self, inputs: dict) -> dict:
        pass

    async def evaluate_agent(self, langsmith_client: Client):
        pass


