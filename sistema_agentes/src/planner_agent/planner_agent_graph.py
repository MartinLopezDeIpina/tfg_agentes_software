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
from src.specialized_agents.SpecializedAgent import SpecializedAgent
from src.utils import tab_all_lines_x_times, print_markdown
from static.prompts import PLANNER_PROMPT_INITIAL, PLANNER_PROMPT_AFTER, SOLVER_AGENT_PROMPT



class PlannerAgentState(AgentState):
    current_step: int
    planner_scratchpad: str


class PlannerAgent(BaseAgent):
    max_steps: int

    available_agents: List[SpecializedAgent]
    orhestrator_agent: OrchestratorAgent

    planner_model: BaseChatModel
    structure_model: BaseChatModel

    def __init__(
            self,
            available_agents: List[SpecializedAgent],
            orchestrator_agent: OrchestratorAgent,
            planner_model: BaseChatModel = ChatOpenAI(model="o3-mini"),
            max_steps: int = 2,
            debug: bool = True
    ):
        super().__init__(
            name="planner_agent",
            model = planner_model,
            debug = debug
        )

    def prepare_prompt(self, state: PlannerAgentState) -> PlannerAgentState:
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


    def process_result(self, agent_state: AgentState) -> AIMessage:
        pass

    async def execute_from_dataset(self, inputs: dict) -> dict:
        pass

    async def evaluate_agent(self, langsmith_client: Client):
        pass




def format_planner_prompt(messages: List[BaseMessage], current_plan: PlannerResponse) -> str:
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

async def execute_planner_reasoner_agent(state: PlannerAgentState) -> PlannerAgentState:
    print("+Ejecutando agente planner")
    messages = state["messages"]
    if len(messages) == 1:
        # si es el primer plan que se hace
        planner_input = messages[0].content
    else:
        planner_input = format_planner_prompt(messages, state["planner_high_level_plan"])

    planner_scratchpad = await state["planner_model"].ainvoke(
        input=planner_input
    )

    state["planner_scratchpad"] = planner_scratchpad.content

    return state

async def execute_planner_structure_agent(state: PlannerAgentState) -> PlannerAgentState:
    structured_llm = state["structure_model"].with_structured_output(PlannerResponse)
    try:
        planner_result = await structured_llm.ainvoke(
            input=state["planner_scratchpad"]
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


def check_finished_plan(state: PlannerAgentState) -> str: 
    plan_max_steps_reached = state["current_step"] >= state["max_steps"]
    
    planner_plan = state["planner_high_level_plan"]
    finished = planner_plan.finished
    
    if plan_max_steps_reached or finished:
        return "finished_plan"
    else:
        return "execute_orchestrator"
    


def prepare_system_message(state: PlannerAgentState) -> PlannerAgentState:

async def finished_plan(state: PlannerAgentState) -> PlannerAgentState:
    print(f"+Ejecutando agente solver")
    sovler_agent_messages = [
        SystemMessage(
            content=SOLVER_AGENT_PROMPT
        ),
        HumanMessage(
            content=state["query"]
        )
    ]
    sovler_agent_messages.extend(state["messages"][1:])
    sovler_agent_messages.append(
        AIMessage(
            content=state["planner_high_level_plan"].to_string()
        )
    )

    finish_result = await state["structure_model"].ainvoke(
        input=sovler_agent_messages
    )
    state["solver_result"] = finish_result.content

    print_markdown(state["solver_result"])


    state["current_step"] += 1
    return state


def create_planner_graph() -> CompiledGraph:
    """
    Devolver el grafo compilado del agente
    """
    graph_builder = StateGraph(PlannerAgentState)

    graph_builder.add_node("prepare", prepare_system_message)
    graph_builder.add_node("execute_planner_reasoner", execute_planner_reasoner_agent)
    graph_builder.add_node("execute_planner_structure", execute_planner_structure_agent)
    graph_builder.add_node("execute_orchestrator", execute_orchestrator_agent)
    graph_builder.add_node("finished_plan", finished_plan)

    graph_builder.add_conditional_edges("execute_planner_structure", check_finished_plan)

    graph_builder.set_entry_point("prepare")
    graph_builder.add_edge("prepare", "execute_planner_reasoner")
    graph_builder.add_edge("execute_planner_reasoner", "execute_planner_structure")
    graph_builder.add_edge("execute_orchestrator", "execute_planner_reasoner")
    graph_builder.set_finish_point("finished_plan")

    return graph_builder.compile()
