import os.path
from abc import ABC, abstractmethod
from typing import List, TypedDict, Callable, Optional

from langchain.smith import RunEvalConfig
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.runnables.graph import CurveStyle, NodeStyles
from langchain_core.stores import BaseStore
from langgraph.graph.graph import CompiledGraph

from langsmith import Client, evaluate, aevaluate, EvaluationResult

from src.evaluators.base_evaluator import BaseEvaluator
from src.evaluators.dataset_utils import search_langsmith_dataset
from src.web_app.stream_manager import StreamManager
from config import GRAPH_IMAGES_RELATIVE_PATH, REPO_ROOT_ABSOLUTE_PATH, default_llm


class AgentState(TypedDict):
    query: str
    messages: List[BaseMessage]
    remaining_steps: int
    is_last_step: bool

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
    prompt: str
    stream_manager: StreamManager

    def __init__(
            self,
            name: str,
            model: BaseChatModel = None,
            debug: bool = True,
            prompt: str = ""
    ):
        self.name = name
        self.model = model or default_llm
        self.debug = True
        self.prompt = prompt
        self.stream_manager = StreamManager.get_instance()

    @abstractmethod
    async def prepare_prompt(self, state, store):
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
    async def evaluate_agent(self, langsmith_client: Client):
        """
        Define los evaluadores específicos a utilizar para la evaluación del agente.
        """

    async def execute_agent_graph_with_exception_handling(self, input: dict):
        """
        Execute agent graph with exception handling and streaming support
        """
        await self.stream_manager.emit_agent_called(
            agent_name=self.name,
        )
        agent_graph = self.create_graph()
        try:
            result = await agent_graph.ainvoke(input=input)
            return result
        except Exception as e:
            error_msg = f"Excepción ejecutando agente {self.name}: {e}"
            print(error_msg)
            await self.stream_manager.emit_error(
                error_message=str(e),
                agent_name=self.name
            )
            return input

    async def execute_from_dataset(self, inputs: dict) -> dict:
        compiled_graph = self.create_graph()

        try:
            run_state = await compiled_graph.ainvoke(
                inputs
            )
            result = self.process_result(run_state)
            return {
                "run_state": run_state,
                "result": result,
            }

        except Exception as e:
            return {
               "error": True
            }

    async def call_agent_evaluation(self, langsmith_client: Client, evaluators: List[BaseEvaluator], max_conc: int = 10, is_prueba: bool = False, evaluation_name: str = None, dataset_name: str = None, dataset_split: str = None):
        if not evaluation_name:
            evaluation_name = f"{self.name} evaluation"

        evaluator_functions = [evaluator.evaluate_metrics for evaluator in evaluators]

        if not dataset_name:
            dataset_name = self.name if not is_prueba else f"{self.name}_prueba"
            dataset_name = f"evaluate_{dataset_name}"

        splits = [dataset_split] if dataset_split else []
        data=langsmith_client.list_examples(dataset_name=dataset_name, splits=splits)

        if not data:
            print(f"Evaluation dataset for {self.name} not found")
            return

        run_function = self.execute_from_dataset

        results = await aevaluate(
            run_function,
            data=data,
            client=langsmith_client,
            evaluators=evaluator_functions,
            max_concurrency=max_conc,
            experiment_prefix=evaluation_name,
        )
        return results

    async def print_agent(self, output_path="."):
        """
        Genera un grafo .mmd y png en la ruta static/images
        """
        absolute_path = os.path.join(REPO_ROOT_ABSOLUTE_PATH, "sistema_agentes", GRAPH_IMAGES_RELATIVE_PATH)

        built_graph = self.create_graph()

        # Obtener el contenido del diagrama Mermaid
        mermaid_str = built_graph.get_graph().draw_mermaid(
            curve_style=CurveStyle.LINEAR,
            node_colors=NodeStyles(first="#ffdfba", last="#baffc9", default="#fad7de"),
            wrap_label_n_words=9,
        )

        # Guardar el archivo .mmd
        mmd_file =f"{absolute_path}/{self.name}.mmd"
        with open(mmd_file, "w") as f:
            f.write(mermaid_str)
        print(f"Diagrama Mermaid guardado en {mmd_file}")

        # Guardar como archivo markdown
        md_file = f"{absolute_path}/{self.name}.md"
        with open(md_file, "w") as f:
            f.write("```mermaid\n")
            f.write(mermaid_str)
            f.write("\n```")
        print(f"Versión Markdown guardada en {md_file}")
