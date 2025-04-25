from typing import List

from langchain_core.messages import BaseMessage, ToolMessage
from langsmith import EvaluationResult
from langsmith.evaluation import EvaluationResults
from pydantic import StrictFloat

from src.BaseAgent import AgentState
from src.evaluators.base_evaluator import BaseEvaluator
from langsmith.schemas import Example, Run

from src.specialized_agents.citations_tool.citations_utils import get_citations_from_conversation_messages
from src.specialized_agents.citations_tool.models import Citation, CitedAIMessage
from src.utils import get_list_from_string_comma_separated_values


def get_cites_from_state_messages(state: AgentState) -> List[Citation]:
    messages = state.get("messages")
    if not messages:
        return []

    citations = get_citations_from_conversation_messages(messages=messages)

    return citations

def get_citation_score(expected_cites_str: List[str], actual_cites: List[Citation]) -> float:
    actual_cites_str = [citation.doc_name for citation in actual_cites]
    actual_cites_str = set(actual_cites_str)

    num_expected_cites = len(expected_cites_str)
    cite_hits = 0
    for cite in actual_cites_str:
        if cite in expected_cites_str:
            cite_hits += 1

    return cite_hits / num_expected_cites

class CiteEvaluator(BaseEvaluator):

    async def evaluate(self, run: Run, example: Example) -> EvaluationResults:
        """
        Evaluador para determinar si la respuesta del agente contiene las citas necesarias
        """

        run_state = run.outputs.get("run_state")

        expected_cites = example.outputs.get("cite")
        if not expected_cites:
            return EvaluationResults(
                results=[]
            )
        expected_cites_list = get_list_from_string_comma_separated_values(expected_cites)

        actual_cites = get_cites_from_state_messages(run_state)
        citation_score = get_citation_score(expected_cites_list, actual_cites)

        return EvaluationResults(
            results=[
                EvaluationResult(
                    key="cite_precision",
                    score=StrictFloat(citation_score)
                )
            ]
        )





