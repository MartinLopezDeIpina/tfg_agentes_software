import functools
from abc import ABC, abstractmethod
from typing import List, TypedDict, Callable

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import create_react_agent

from langsmith import Client, evaluate, aevaluate

from src.mcp_client.mcp_multi_client import MCPClient
from src.utils import tab_all_lines_x_times
from src.eval_agents.dataset_utils import search_langsmith_dataset
from src.eval_agents.tool_precision_evaluator import tool_precision

class AgentState(TypedDict):
    query: str
    messages: List[BaseMessage]

class BaseAgent(ABC):
    """
    Combinación de grafos de Langgraph con clases de python:
        -Se aprovecha la herencia de python para reutilizar componentes entre agentes de forma clara.
        -Se aprovechan los grafos de langgraph para definir la lógica del agente.
    El estado del agente contiene información de la ejecución específica, el objeto del agente contiene información que perdura entre ejecuciones.
    """

    name: str
    model: BaseChatModel
    debug: bool

    def __init__(
            self,
            name: str,
            model: BaseChatModel = None,
            debug: bool = True
    ):
        self.name = name
        self.model = model or ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
        self.debug = True

    @abstractmethod
    async def prepare_prompt(self, query: str) -> List[BaseMessage]:
        """
        Prepara los mensajes del sistema y usuario para este agente.
        Utiliza algunas de las tools para proporcionar información contextual al agente.
        """

    @abstractmethod
    def process_result(self, agent_state: AgentState) -> AIMessage:
        """
        Una vez ejecutado el grafo del agente, obtener el resultado final.
        """

    @abstractmethod
    def create_graph(self) -> CompiledGraph:
        """
        Devolver el grafo compilado del agente
        """

    @abstractmethod
    async def execute_from_dataset(self, inputs: dict) -> dict:
        """
        Define la lógica de ejecución del grafo para un ejemplo del dataset de evaluación.
        """

    @abstractmethod
    async def evaluate_agent(self, langsmith_client: Client):
        """
        Define los evaluadores específicos a utilizar para la evaluación del agente.
        """

    async def call_agent_evaluation(self, langsmith_client: Client, evaluators: List[Callable], max_conc: int = 10):
        dataset = search_langsmith_dataset(langsmith_client = langsmith_client, agent_name=self.name)
        if not dataset:
            print(f"Evaluation dataset for {self.name} not found")
            return

        run_function = self.execute_from_dataset

        results = await aevaluate(
            run_function,
            data=dataset,
            client=langsmith_client,
            evaluators=evaluators,
            max_concurrency=max_conc
        )
        return results



        
