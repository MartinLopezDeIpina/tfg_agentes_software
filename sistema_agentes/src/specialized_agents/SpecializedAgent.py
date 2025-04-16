import functools
from abc import ABC, abstractmethod
from typing import List, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import create_react_agent

from langsmith import Client, evaluate, aevaluate
from langsmith.evaluation import EvaluationResults

from src.BaseAgent import AgentState, BaseAgent
from src.mcp_client.mcp_multi_client import MCPClient
from src.utils import tab_all_lines_x_times
from src.eval_agents.dataset_utils import search_langsmith_dataset
from src.eval_agents.tool_precision_evaluator import tool_precision

class SpecializedAgent(BaseAgent):

    description: str
    tools_str: List[str]
    tools: List[BaseTool]
    mcp_client: MCPClient

    def __init__(
        self,
        name: str,
        description: str,
        model: BaseChatModel = None,
        tools_str: List[str] = None,
    ):
        super().__init__(
            name=name,
            model = model or ChatOpenAI(model="gpt-4o-mini", temperature=0.0),
            debug=True
        )
    
        self.description = description
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
            print(f"-->Ejecutando agente: {self.name}")

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

    async def execute_from_dataset(self, inputs: dict) -> dict:
        query = inputs.get("query")

        compiled_graph = self.create_graph()

        run = await compiled_graph.ainvoke({
            "query":query,
            "messages":[]
        })
        return run
    
    async def evaluate_agent(self, langsmith_client: Client):
        agent_tool_evaluator = functools.partial(tool_precision, num_tools=len(self.tools))

        result = await self.call_agent_evaluation(langsmith_client, [agent_tool_evaluator])
        return result


