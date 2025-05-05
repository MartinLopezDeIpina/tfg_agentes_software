from typing import List, Tuple

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph
from langsmith import Client

from src.BaseAgent import AgentState, BaseAgent
from src.formatter_agent.models import FormatterResponse
from src.structured_output_validator import execute_structured_llm_with_validator_handling
from src.planner_agent.models import PlannerResponse, PlanAIMessage
from src.planner_agent.state import MainAgentState
from src.specialized_agents.citations_tool.citations_utils import get_citations_from_conversation_messages
from src.specialized_agents.citations_tool.models import CitedAIMessage, Citation
from src.utils import tab_all_lines_x_times, print_markdown
from static.prompts import SOLVER_AGENT_PROMPT
from config import default_llm

def get_citations_string(citations: List[Citation]) -> str:
    citation_str = ""
    for i, citation in enumerate(citations):
        citation_str+=tab_all_lines_x_times(
            f"""Citation id {i}:
    {tab_all_lines_x_times(citation.to_string())}"""
        )
    return citation_str

# todo: se podría hacer un formatter que solo coja el último mensaje y las citas y solo haga print del resultado, para usarlo con el ReactOrchestratorAgent
class FormatterAgentState(AgentState):
    available_citations: List[Citation]

    current_try: int
    format_error: bool

    formatted_result: str
    formatter_citations: List[Citation]

class FormatterAgent(BaseAgent):

    max_tries: int

    def __init__(
            self,
            model: BaseChatModel= default_llm,
            debug: bool = True,
            max_tries: int = 2
                 ):
        super().__init__(
            name="formatter_agent",
            model=model,
            debug=debug
                         )
        self.max_tries = max_tries

    async def prepare_prompt(self, state: FormatterAgentState) -> FormatterAgentState:
        print(f"+Ejecutando agente formatter")
        state["current_try"] = 0
        
        available_cites = get_citations_from_conversation_messages(state.get("messages"))
        state["available_citations"] = available_cites
        cites_str = get_citations_string(available_cites)

        formatter_agent_messages = [
            SystemMessage(
                content=SOLVER_AGENT_PROMPT.format(
                    available_cites=cites_str
                )
            ),
            HumanMessage(
                content=state["query"]
            )
        ]
        for message in state["messages"][1:]:
            if isinstance(message, CitedAIMessage) or isinstance(message, PlanAIMessage):
                formatter_agent_messages.append(message.format_to_ai_message())
            else:
                formatter_agent_messages.append(message)

        state["messages"] = formatter_agent_messages
        return state

    async def execute_formatter(self, state: FormatterAgentState):
        """
        Se hacen varios intentos de formatear la salida con las citas correctas.
        Cada intento a su vez reintenta una vez con el parser de langchain.
        """
        state["current_try"] += 1
        try:
            prompt = state["messages"]
            formatter_result = await execute_structured_llm_with_validator_handling(
                prompt=prompt,
                output_schema=FormatterResponse,
                llm=self.model,
                # Solo validar una vez el parsing, sino volver a intentarlo en el propio grafo del formatter
                max_retries=1
            )

            output_citations = formatter_result.citations
            formatter_citations = []
            available_citations = state["available_citations"]
            for output_citation in output_citations:
                try:
                    formatter_citations.append(available_citations[output_citation.cite_id])
                except Exception as e:
                    print(f"Formatter no ha formateado bien una cita: {e}")

            state["formatted_result"] = formatter_result.response
            state["formatter_citations"] = formatter_citations
            state["format_error"] = False

        except Exception as e:
            state["format_error"] = True
            print(f"Excepción ejecutando agente formatter")

        return state

    def retry_formatter_if_exception_raised(self, state: FormatterAgentState):
        if state.get("format_error") and state["current_try"] <= self.max_tries:
            return "formatter"
        else:
            return "print"

    def print_formatted_result(self, state: FormatterAgentState):
        print("\n\n")
        print_markdown(state["formatted_result"])
        citations_markdown = ""
        for citation in state["formatter_citations"]:
            citations_markdown+=("\n```\n" + citation.to_string() + "\n```")
        print_markdown(citations_markdown)

    def create_graph(self) -> CompiledGraph:
        graph_builder = StateGraph(FormatterAgentState)

        graph_builder.add_node("prepare", self.prepare_prompt)
        graph_builder.add_node("formatter", self.execute_formatter)
        graph_builder.add_node("print", self.print_formatted_result)

        graph_builder.add_edge("prepare", "formatter")
        graph_builder.add_conditional_edges("formatter", self.retry_formatter_if_exception_raised)

        graph_builder.set_entry_point("prepare")
        graph_builder.set_finish_point("print")

        return graph_builder.compile()

    def process_result(self, agent_state: FormatterAgentState) -> CitedAIMessage:
        response = agent_state.get("formatted_result")
        citations = agent_state.get("formatter_citations")

        message = AIMessage(
            content=response
        )
        return CitedAIMessage(
            message=message,
            citations=citations
        )

    def execute_from_dataset(self, inputs: dict) -> dict:
        pass

    def evaluate_agent(self, langsmith_client: Client):
        pass




