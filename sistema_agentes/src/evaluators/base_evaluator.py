from abc import abstractmethod
from typing import Callable
from langsmith.schemas import Example, Run
from langsmith import EvaluationResult
from langsmith.evaluation import EvaluationResults


class BaseEvaluator:

    @abstractmethod
    async def evaluate(self, run: Run, example: Example) -> EvaluationResults:
        """
        Definir las métricas de evaluación.
        """

    async def evaluate_metrics(self, run: Run, example: Example) -> EvaluationResults:
        """
        Comprobar si ha habido errores en la ejecución del agente.
        """
        if run.outputs.get("error"):
            return EvaluationResults(
                results=[]
            )

        else:
            return await self.evaluate(run, example)

