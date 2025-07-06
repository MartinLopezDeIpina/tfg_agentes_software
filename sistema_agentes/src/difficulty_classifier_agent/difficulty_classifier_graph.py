import os

from huggingface_hub import login
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph
from langgraph.graph.graph import CompiledGraph
from langsmith import Client
from transformers import pipeline

from config import default_llm
from src.BaseAgent import AgentState, BaseAgent
from src.evaluators.question_difficulty_evaluator import QuestionDifficultyEvaluator
from src.difficulty_classifier_agent.few_shots import classifier_few_shots
from src.difficulty_classifier_agent.models import ClassifierResponse
from src.main_agent.main_graph import MainAgent
from src.specialized_agents.citations_tool.models import CitedAIMessage
from src.structured_output_validator import execute_structured_llm_with_validator_handling
from static.prompts import CLASSIFIER_AGENT_PROMPT, CLASSIFIER_BERT_PROMPT


class ClassifierAgentState(AgentState):
    classifier_result: ClassifierResponse

class ClassifierAgent(BaseAgent):
    use_tuned_model = bool

    def __init__(self,
                 use_tuned_model = True,
                 ):

        if use_tuned_model:
            login(token=os.getenv("HUGGINGFACEHUB_API_TOKEN"))
            model_id = "MartinElMolon/RoBERTa_question_difficulty_classifier"
            model = pipeline("text-classification", model=model_id)
            self.prompt = CLASSIFIER_BERT_PROMPT
        else:
            self.prompt = CLASSIFIER_AGENT_PROMPT.format(few_shot_examples=classifier_few_shots, question="{question}")
            model = default_llm

        super().__init__(
            name="classifier_agent",
            model = model,
            debug=True,
            prompt = self.prompt
        )
        self.use_tuned_model = use_tuned_model

    async def prepare_prompt(self, state, store):
        print(f"Ejecutando agente {self.name}")
        state["messages"] = [
            SystemMessage(
               content=self.prompt.format(
                  question=state["query"],
               )
            )
        ]
        return state
    
    async def execute_classifier_model(self, state: ClassifierAgentState):
        if self.use_tuned_model:
            prompt_content = state.get("messages")[0].content
            result = self.model(prompt_content)
            if result[0].get("label") == "LABEL_0":
                response = ClassifierResponse(difficulty="EASY")
            else:
                response = ClassifierResponse(difficulty="HARD")
        else:
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
        graph_builder.add_node("execute", self.execute_classifier_model)

        graph_builder.set_entry_point("prepare")
        graph_builder.add_edge("prepare", "execute")

        return graph_builder.compile()

    async def evaluate_agent(self, langsmith_client: Client):
        evaluators = [QuestionDifficultyEvaluator()]

        result = await self.call_agent_evaluation(langsmith_client, evaluators)
        return result
