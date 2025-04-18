from typing import List

from langchain_openai import ChatOpenAI
from langsmith import EvaluationResult
from langsmith.evaluation import EvaluationResults
from langsmith.schemas import Example, Run
from pydantic import StrictFloat

from src.eval_agents.base_evaluator import BaseEvaluator
from src.eval_agents.models import JudgeLLMResponse
from src.utils import get_list_from_string_comma_separated_values, get_list_string_with_indexes
from static.prompts import LLM_JUDGE_PROMPT

async def get_llm_as_a_judge_evaluation(solution_list: List[str], run_result: dict, run_state: dict) -> JudgeLLMResponse:
    model = ChatOpenAI(model="gpt-4o-mini")
    structured_llm = model.with_structured_output(JudgeLLMResponse)
    ground_truth_list = get_list_string_with_indexes(solution_list)
    model_evaluation = await structured_llm.ainvoke(
        input=LLM_JUDGE_PROMPT.format(
            ground_truth=ground_truth_list,
            generated_solution=run_result,
            query=run_state.get("query")
        )
    )
    if not isinstance(ground_truth_list, JudgeLLMResponse):
        model_evaluation = JudgeLLMResponse.model_validate(model_evaluation)

    return model_evaluation

class JudgeLLMEvaluator(BaseEvaluator):

    async def evaluate(self, run: Run, example: Example) -> EvaluationResults:
        """
        Evaluador para determinar si las respuestas de los agentes son correctas.
        Un agente llm-judge determina si la respuesta es correcta partiendo de la instancia del dataset con la solución anotada.
        La solución son "conceptos" que la respuesta del agente debe contener.
        En caso de ser un ejemplo anotado como imposible de responder, el juez determina si el modelo ha "alucinado", o si este ha determinado que no se contiene suficiente información.
        """

        run_result = run.outputs.get("result")
        run_state = run.outputs.get("run_state")
        run_solution = example.outputs.get("solution")
        solution_possible = example.outputs.get("possible")

        if solution_possible:
            solution_list = get_list_from_string_comma_separated_values(run_solution)
        else:
            solution_list = []

        try:
            evaluation_results = []

            model_evaluation = await get_llm_as_a_judge_evaluation(solution_list, run_result, run_state)

            if solution_possible:
                right_concepts = len([elem for elem in model_evaluation.corrections if elem.is_included])
                solution_len = len(solution_list)
                score = right_concepts / solution_len if len(solution_list) > 0 else 0.0
                evaluation_results.append(
                    EvaluationResult(
                        key="llm-as-a-judge",
                        score=StrictFloat(score)
                    )
                )
            else:
                if model_evaluation.tried_to_respond:
                    hallucination_score = 0.0
                else:
                    hallucination_score = 1.0

                hallucination_score = StrictFloat(hallucination_score)
                evaluation_results.append(
                    EvaluationResult(
                        key="hallucination",
                        score=hallucination_score
                    )
                )
            return EvaluationResults(
                results=evaluation_results,
            )

        except Exception as e:
            print(f"error evaluating: {e}")
            return EvaluationResult.FAILED







