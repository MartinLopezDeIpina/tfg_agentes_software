from typing import List
from langchain_core.messages import BaseMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.graph.graph import CompiledGraph
from langsmith import Client

from config import default_llm
from src.BaseAgent import BaseAgent, AgentState


class DummyAgent(BaseAgent):
    """
    Agente simple que ejecuta el modelo directamente sin lógica compleja.
    Ideal para tareas básicas como generación de títulos, resúmenes simples, etc.
    """

    def __init__(self, name: str = "dummy_agent", model=default_llm, debug: bool = True, prompt: str = ""):
        super().__init__(name, model, debug, prompt)

    async def prepare_prompt(self, state: AgentState, store=None) -> AgentState:
        messages = state.get("messages", [])
        if "query" in state:
            messages.append(SystemMessage(content=state.get("query")))
        state["messages"] = messages
        return state

    def process_result(self, agent_state: AgentState) -> AIMessage:
        messages = agent_state.get("messages", [])

        # Buscar el último mensaje AI
        for message in reversed(messages):
            if isinstance(message, AIMessage):
                return message

        return AIMessage(content="No response generated")

    async def call_model(self, state: AgentState) -> AgentState:
            response = await self.model.ainvoke(state.get("messages"))
            state["messages"] = state.get("messages", []) + [response]

            return state

    def create_graph(self) -> CompiledGraph:
        workflow = StateGraph(AgentState)

        workflow.add_node("prepare_prompt", self.prepare_prompt)
        workflow.add_node("call_model", self.call_model)

        workflow.set_entry_point("prepare_prompt")
        workflow.add_edge("prepare_prompt", "call_model")

        return workflow.compile()

    async def evaluate_agent(self, langsmith_client: Client):
        pass