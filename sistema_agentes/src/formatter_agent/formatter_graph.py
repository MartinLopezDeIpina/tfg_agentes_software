from typing import List

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph
from langsmith import Client

from src.BaseAgent import AgentState, BaseAgent
from src.planner_agent.models import PlannerResponse
from src.planner_agent.state import MainAgentState
from src.specialized_agents.citations_tool.models import CitedAIMessage
from src.utils import tab_all_lines_x_times, print_markdown
from static.prompts import SOLVER_AGENT_PROMPT
from config import default_llm

class FormatterAgent(BaseAgent):
    def __init__(
            self,
            model: BaseChatModel= default_llm,
            debug: bool = True
                 ):
        super().__init__(
            name="formatter_agent",
            model=model,
            debug=debug
                         )

    async def prepare_prompt(self, state: MainAgentState) -> MainAgentState:
        print(f"+Ejecutando agente formatter")
        formatter_agent_messages = [
            SystemMessage(
                content=SOLVER_AGENT_PROMPT
            ),
            HumanMessage(
                content=state["query"]
            )
        ]
        for message in state["messages"][1:]:
            if isinstance(message, CitedAIMessage):
                formatter_agent_messages.append(message.format_to_ai_message())
            else:
                formatter_agent_messages.append(message)

        finish_result = await self.model.ainvoke(
            input=formatter_agent_messages
        )
        state["formatter_result"] = finish_result.content

        print_markdown(state["formatter_result"])

        return state


    def create_graph(self) -> CompiledGraph:
        graph_builder = StateGraph(MainAgentState)

        graph_builder.add_node("prepare", self.prepare_prompt)

        graph_builder.set_entry_point("prepare")

        return graph_builder.compile()

    def process_result(self, agent_state: AgentState) -> AIMessage:
        pass

    def execute_from_dataset(self, inputs: dict) -> dict:
        pass

    def evaluate_agent(self, langsmith_client: Client):
        pass




