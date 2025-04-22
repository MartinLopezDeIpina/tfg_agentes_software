import functools
from abc import ABC, abstractmethod
from typing import List, TypedDict

from jedi.inference.recursion import recursion_limit
from langchain.chains.question_answering.map_reduce_prompt import messages
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import create_react_agent

from langsmith import Client, evaluate, aevaluate
from langsmith.evaluation import EvaluationResults

from config import default_llm
from src.BaseAgent import AgentState, BaseAgent
from src.eval_agents.cite_references_evaluator import CiteEvaluator
from src.eval_agents.llm_as_judge_evaluator import JudgeLLMEvaluator
from src.mcp_client.mcp_multi_client import MCPClient
from src.specialized_agents.citations_tool.citations_tool_factory import create_citation_tool
from src.specialized_agents.citations_tool.citations_utils import get_citations_from_conversation_messages
from src.specialized_agents.citations_tool.models import DataSource, CitedAIMessage
from src.utils import tab_all_lines_x_times
from src.eval_agents.dataset_utils import search_langsmith_dataset
from src.eval_agents.tool_precision_evaluator import ToolPrecisionEvaluator


class SpecializedAgent(BaseAgent):

    description: str
    tools_str: List[str]
    tools: List[BaseTool]
    mcp_client: MCPClient
    data_sources: List[DataSource]
    #todo + checkear frontend en agente código
    config: RunnableConfig

    def __init__(
        self,
        name: str,
        description: str,
        prompt: str = "",
        model: BaseChatModel = default_llm,
        tools_str: List[str] = None,
        data_sources: List[DataSource] = None,
    ):
        super().__init__(
            name=name,
            model = model,
            debug=True,
            prompt = prompt
        )

        self.description = description
        self.tools_str = tools_str or []
        self.data_sources = data_sources or []


    @abstractmethod
    async def connect_to_mcp(self):
        """
        Conectarse al cliente mcp y obtener las tools
        """

    async def create_citation_data_source(self):
        if self.data_sources:
            for data_source in self.data_sources:
                await data_source.set_available_documents(self.tools)

            self.tools.append(
                create_citation_tool(
                    data_sources=self.data_sources
                )
            )

    async def init_agent(self):
        """
        Conecta el agente al servidor MCP e inicializa el sistema de referenciado de citas
        """
        await self.connect_to_mcp()
        await self.create_citation_data_source()

    async def cleanup(self):
        """
        Limpiar la conexión al cliente mcp
        """
        if self.mcp_client:
            await self.mcp_client.cleanup()

    def process_result(self, agent_state: AgentState) -> CitedAIMessage:
        """
        Una vez ejecutado el grafo del agente, obtener el resultado final.
        """
        ai_messages = agent_state.get("messages")

        if ai_messages:
            response_message = ai_messages[-1]
            citations = get_citations_from_conversation_messages(ai_messages) or []

            return CitedAIMessage(
                message=response_message,
                citations=citations
            )
        else:
            final_result = CitedAIMessage(
                message=AIMessage(content="Error procesando respuesta"),
                citations = []
            )

        return final_result

    def create_graph(self) -> CompiledGraph:
        """
        Devolver el grafo compilado del agente
        """
        graph_builder = StateGraph(AgentState)

        react_graph = create_react_agent(
            model=self.model,
            tools=self.tools,
        )

        graph_builder.add_node("prepare", self.prepare_prompt)
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

    @staticmethod
    def get_tools_from_run_state(state: AgentState) -> List[str]:
        messages = state["messages"]
        called_tools = []
        for message in messages[1:]:
            if message.type == "tool":
                called_tools.append(message.name)
        return called_tools

    async def evaluate_agent(self, langsmith_client: Client):
        evaluators = [
            ToolPrecisionEvaluator(self.get_tools_from_run_state),
            JudgeLLMEvaluator(),
            CiteEvaluator()
        ]

        result = await self.call_agent_evaluation(langsmith_client, evaluators)
        return result


