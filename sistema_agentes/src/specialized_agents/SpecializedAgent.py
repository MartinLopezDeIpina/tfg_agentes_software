import uuid
from abc import abstractmethod
from typing import List
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import END
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph
from langgraph.prebuilt import create_react_agent
from langgraph.store.postgres import AsyncPostgresStore

from langsmith import Client

from config import default_llm
from src.BaseAgent import AgentState, BaseAgent
from src.db.langchain_store_utils import get_and_manage_agent_memory_docs, save_agent_memory_in_store
from src.evaluators.cite_references_evaluator import CiteEvaluator
from src.evaluators.llm_as_judge_evaluator import JudgeLLMEvaluator
from src.mcp_client.mcp_multi_client import MCPClient
from src.db.postgres_connection_manager import PostgresPoolManager
from src.specialized_agents.citations_tool.citations_tool_factory import create_citation_tool
from src.specialized_agents.citations_tool.citations_utils import get_citations_from_conversation_messages
from src.specialized_agents.citations_tool.models import DataSource, CitedAIMessage
from src.utils import tab_all_lines_x_times, get_memory_prompt_from_docs
from src.evaluators.tool_precision_evaluator import ToolPrecisionEvaluator

from static.prompts import REACT_SUMMARIZER_SYSTEM_PROMPT, MEMORY_SUMMARIZER_PROMPT


class SpecializedAgentState(AgentState):
    recursion_limit_exceded: bool
    memory_docs: List[AIMessage]

class SpecializedAgent(BaseAgent):

    description: str
    tools_str: List[str]
    prompt_only_tools_str: List[str]
    tools: List[BaseTool]
    mcp_client: MCPClient
    data_sources: List[DataSource]

    max_steps: int
    react_graph: CompiledGraph
    checkpointer: BaseCheckpointSaver
    use_memory: bool
    k_memory_docs: int

    def __init__(
        self,
        name: str,
        description: str,
        prompt: str = "",
        model: BaseChatModel = default_llm,
        tools_str: List[str] = None,
        prompt_only_tools: List[str] = None,
        data_sources: List[DataSource] = None,
        max_steps: int = 10,
        use_memory: bool = False,
        k_memory_docs: int = 4
    ):
        super().__init__(
            name=name,
            model = model,
            debug=True,
            prompt = prompt
        )

        self.description = description
        self.tools_str = tools_str or []
        self.prompt_only_tools_str = prompt_only_tools or []
        self.data_sources = data_sources or []
        self.max_steps = max_steps
        self.use_memory = use_memory
        self.k_memory_docs = k_memory_docs


    @abstractmethod
    async def connect_to_mcp(self):
        """
        Conectarse al cliente mcp y obtener las tools
        """

    async def add_additional_tools(self):
        """
        Sobreescribir para añadir herramientas que no están disponibles en el servidor mcp en el caso de que sean necesarias
        """
        pass

    async def prepare_prompt(self, state: SpecializedAgentState, store: AsyncPostgresStore) -> SpecializedAgentState:
        if self.use_memory:
            try:
                memory_docs = await get_and_manage_agent_memory_docs(store=store, agent_name=self.name, query=state.get("query"), k_docs=self.k_memory_docs)
                state["memory_docs"] = get_memory_prompt_from_docs(memory_docs)
            except Exception as e:
                print(f"Error obteniendo memoria en agente {self.name}")
                state["memory_docs"] = []
        else:
            state["memory_docs"] = []

        return state

    def get_agent_tools(self):
        return [tool for tool in self.tools if tool.name not in self.prompt_only_tools_str]

    async def create_citation_data_source(self):
        if self.data_sources:
            for data_source in self.data_sources:
                await data_source.set_available_documents(self.tools)

            self.tools.append(
                create_citation_tool(
                    data_sources=self.data_sources
                )
            )

    async def init_checkpointer(self):
        """
        Configura el checkpointer de PostgreSQL.
        Si falla la conexión utilizar un MemorySaver normal sin manejo de concurrencia.
        """
        try:
            postgres_manager = await PostgresPoolManager.get_instance()
            self.checkpointer = postgres_manager.get_checkpointer()

        except Exception as e:
            print(f"Error conectando a postgresql, iniciando checkpointer básico: {e}")
            self.checkpointer = MemorySaver()

    async def init_agent(self):
        """
        Conecta el agente al servidor MCP e inicializa el sistema de referenciado de citas
        """
        await self.connect_to_mcp()
        await self.add_additional_tools()
        await self.create_citation_data_source()
        await self.init_checkpointer()

    async def cleanup(self):
        """
        Limpiar la conexión al cliente mcp
        """
        if self.mcp_client:
            await self.mcp_client.cleanup()

    def process_result(self, agent_state: SpecializedAgentState) -> CitedAIMessage:
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

    async def call_langgraph_react_graph(self, state: SpecializedAgentState):
        """
        Llamar al grafo ReAct de langgraph con el máximo de steps definido
        """
        messages = state.get("messages")
        thread_id = str(uuid.uuid4())
        config=RunnableConfig(
            recursion_limit=self.max_steps,
            configurable={"thread_id": thread_id}
        )

        try:
            result = await self.react_graph.ainvoke(
                input={
                    "messages": messages,
                },
                config=config
            )
            if result["messages"][-1].content == "Sorry, need more steps to process this request.":
                raise Exception("Recursion limit reached")
            return result
        except Exception as e:
            print(f"Límite de {self.max_steps} pasos alcanzado en agente {self.name}")
            state["recursion_limit_exceded"] = True
            last_state = await self.checkpointer.aget(config)
            messages = last_state["channel_values"].get("messages", [])
            state["messages"] = messages
            return state

    async def generate_summarized_response(self, state: SpecializedAgentState):
        messages = state.get("messages")
        if not messages:
            messages = []

        new_system_message = SystemMessage(
            content=REACT_SUMMARIZER_SYSTEM_PROMPT
        )

        if len(messages) > 0:
            messages[0] = new_system_message
        else:
            messages.append(new_system_message)

        try:
            summarizer_response = await self.model.ainvoke(messages)
            state["messages"].append(summarizer_response)
            return state
        except Exception as e:
            state["messages"].append(AIMessage(content="Error ejecutando agente especializado"))
            return state

    def route_memory_summarizer(self, state: SpecializedAgentState):
        if self.use_memory:
            return "memory_summarizer"
        return END

    def check_react_recursion_limit(self, state: SpecializedAgentState):
        recursion_limit_exceded = state.get("recursion_limit_exceded")

        if recursion_limit_exceded:
            return "response_summarizer"
        else:
            return "memory_check"

    async def execute_memory_summarizer_agent(self, state, store):
        available_cites = get_citations_from_conversation_messages(state.get("messages"))
        available_cites_serialized = [str(cite) for cite in available_cites]
        response_message = state.get("messages")[-1]

        prompt = [
            SystemMessage(
                content=MEMORY_SUMMARIZER_PROMPT
            ),
            response_message
        ]

        summarizer_response = await self.model.ainvoke(prompt)
        stored_data = {
            "concept": summarizer_response.content,
            "cites": available_cites_serialized,
            "access_count": 0
        }

        await save_agent_memory_in_store(
            store=store,
            values = stored_data,
            key=uuid.uuid4().__str__(),
            agent_name=self.name
        )

    def create_graph(self) -> CompiledGraph:
        """
        Devolver el grafo compilado del agente
        """
        agent_tools = self.get_agent_tools()
        self.react_graph = create_react_agent(
            model=self.model,
            tools=agent_tools,
            checkpointer=self.checkpointer,
        )
        graph_builder = StateGraph(SpecializedAgentState)

        graph_builder.add_node("prepare", self.prepare_prompt)
        graph_builder.add_node("react", self.call_langgraph_react_graph)
        graph_builder.add_node("response_summarizer", self.generate_summarized_response)
        graph_builder.add_node("memory_summarizer", self.execute_memory_summarizer_agent)
        # nodo placeholder para ir al condicional directamente
        graph_builder.add_node("memory_check", lambda x: x)

        graph_builder.set_entry_point("prepare")
        graph_builder.add_edge("prepare", "react")
        graph_builder.add_conditional_edges("react", self.check_react_recursion_limit)
        graph_builder.add_conditional_edges("memory_check", self.route_memory_summarizer)
        graph_builder.add_conditional_edges("response_summarizer", self.route_memory_summarizer)

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


def get_agents_description(available_agents: List[SpecializedAgent]):
    agents_description = ""
    for agent in available_agents:
        agents_description += f"\n-{agent.to_string()}"

    return agents_description






