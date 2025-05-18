from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph
from langsmith import Client

from config import default_llm
from src.BaseAgent import AgentState, BaseAgent
from src.evaluators.question_difficulty_evaluator import QuestionDifficultyEvaluator
from src.specialized_agents.difficulty_classifier_agent.few_shots import classifier_few_shots
from src.specialized_agents.difficulty_classifier_agent.models import ClassifierResponse
from src.structured_output_validator import execute_structured_llm_with_validator_handling
from static.prompts import CLASSIFIER_AGENT_PROMPT


class ClassifierAgentState(AgentState):
    classifier_result: ClassifierResponse

class ClassifierAgent(BaseAgent):
    def __init__(self,
                 model: BaseChatModel = default_llm,
                 prompt: str = ""
                 ):


        super().__init__(
            name="classifier_agent",
            model = model,
            debug=True,
            prompt = prompt
        )

    async def prepare_prompt(self, state, store):
        print(f"Ejecutando agente {self.name}")
        state["messages"] = [
            SystemMessage(
               content=CLASSIFIER_AGENT_PROMPT.format(
                  question=state["query"],
                  few_shot_examples=classifier_few_shots 
               ) 
            )
        ]
        return state
    
    async def execute_model(self, state: ClassifierAgentState):
        response = await execute_structured_llm_with_validator_handling(
            prompt=state.get("messages"),
            output_schema=ClassifierResponse
        )
        state["classifier_result"] = response

        return state

    @classmethod
    def process_result(cls, agent_state: ClassifierAgentState) -> ClassifierResponse:
        result = agent_state["classifier_result"]
        return result

    def create_graph(self) -> CompiledGraph:
        graph_builder = StateGraph(ClassifierAgentState)

        graph_builder.add_node("prepare", self.prepare_prompt)
        graph_builder.add_node("execute", self.execute_model)

        graph_builder.set_entry_point("prepare")
        graph_builder.add_edge("prepare", "execute")

        return graph_builder.compile()

    async def evaluate_agent(self, langsmith_client: Client):
        evaluators = [QuestionDifficultyEvaluator()]

        result = await self.call_agent_evaluation(langsmith_client, evaluators)
        return result
