from langsmith import EvaluationResult
from langsmith.evaluation import EvaluationResults
from langsmith.schemas import Run, Example
from pydantic import StrictFloat

from src.evaluators.base_evaluator import BaseEvaluator


class QuestionDifficultyEvaluator(BaseEvaluator):
    async def evaluate(self, run: Run, example: Example) -> EvaluationResults:
        """
        Evaluador para determinar si la clasificación del agente clasificador es correcta
        """
        run_state = run.outputs.get("run_state")

        expected_class = example.outputs.get("class")
        actual_class = run_state.get("classifier_result").difficulty

        if actual_class == expected_class:
            difficulty_score = 1.0
        else:
            difficulty_score = 0.0

        return EvaluationResults(
            results=[
                EvaluationResult(
                    key="difficulty_precission",
                    score=StrictFloat(difficulty_score)
                )
            ]
        )

