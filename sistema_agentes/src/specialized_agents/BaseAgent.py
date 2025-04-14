from abc import ABC, abstractmethod
from typing import List, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import create_react_agent

from src.mcp_client.mcp_multi_client import MCPClient
from src.utils import tab_all_lines_x_times


class AgentState(TypedDict):
    query: str
    messages: List[BaseMessage]

class BaseAgent(ABC):

    name: str
    description: str
    tools_str: List[str]
    tools: List[BaseTool]
    model: BaseChatModel
    mcp_client: MCPClient

    def __init__(
            self,
            name: str,
            description: str,
            model: BaseChatModel = None,
            tools_str: List[str] = None,
    ):
        self.name = name
        self.description = description
        self.model = model or ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
        self.tools_str = tools_str or []

    @abstractmethod
    async def connect_to_mcp(self):
        """
        Conectarse al cliente mcp y obtener las tools
        """

    async def cleanup(self):
        """
        Limpiar la conexión al cliente mcp
        """
        if self.mcp_client:
            await self.mcp_client.cleanup()

    @abstractmethod
    async def prepare_prompt(self, query: str) -> List[BaseMessage]:
        """
        Prepara los mensajes del sistema y usuario para este agente.
        Utiliza algunas de las tools para proporcionar información contextual al agente.
        """
        pass

    def process_result(self, agent_state: AgentState) -> AIMessage:
        """
        Una vez ejecutado el grafo del agente, obtener el resultado final.
        """
        ai_messages = [msg for msg in agent_state["messages"] if isinstance(msg, AIMessage)]

        if ai_messages:
            final_result = ai_messages[-1].content
        else:
            final_result = AIMessage(
                content="An error occurred while processing the request"
            )

        return final_result

    def create_graph(self) -> CompiledGraph:
        """
        Devolver el grafo compilado del agente
        """
        graph_builder = StateGraph(AgentState)

        async def prepare_node(state: AgentState) -> AgentState:
            state["messages"] = await self.prepare_prompt(state["query"])
            return state

        react_graph = create_react_agent(model=self.model, tools=self.tools)

        graph_builder.add_node("prepare", prepare_node)
        graph_builder.add_node("react", react_graph)

        graph_builder.set_entry_point("prepare")
        graph_builder.add_edge("prepare", "react")
        graph_builder.set_finish_point("react")

        return graph_builder.compile()
    
    def to_string(self):
        string = ""
        string += f"{self.name}:\n"
        string += tab_all_lines_x_times(self.description)
        return string
        
        
