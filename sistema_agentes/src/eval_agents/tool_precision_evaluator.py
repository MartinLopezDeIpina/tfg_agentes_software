from typing import List, Tuple, Set

from langsmith import EvaluationResult
from langsmith.evaluation import EvaluationResults
from langsmith.schemas import Example, Run
from pydantic import StrictFloat

from src.eval_agents.base_evaluator import BaseEvaluator
from src.utils import get_list_from_string_comma_separated_values

def get_evaluation_result(tool_precision: StrictFloat, necessary_tool_precision: float, unnecessary_tool_precision: float) -> EvaluationResults:
    return EvaluationResults(
        results=[
            EvaluationResult(
                key="tool_precision",
                score=tool_precision,
                extra={
                    "necessary_tool_precision": necessary_tool_precision,
                    "unnecessary_tool_precision": unnecessary_tool_precision,
                }
            )
        ]
    )

def get_num_necessary_and_unnecesary_called_tools(called_tools: Set[str], necessary_tools: List[str], unnecessary_tools: List[str]) -> Tuple[int, int]:
    num_called_necesary_tools = 0
    num_called_unnecessary_tools = 0
    for called_tool in called_tools:
        if called_tool in necessary_tools:
            num_called_necesary_tools += 1
        elif called_tool in unnecessary_tools:
            num_called_unnecessary_tools += 1
    return num_called_necesary_tools, num_called_unnecessary_tools

def calculate_tool_precision(
        num_necessary_tools: int,
        num_unnecessary_tools: int,
        num_called_necessary_tools: int,
        num_called_unnecessary_tools: int
) -> Tuple[float, float, float]:
    """
    Caluclar métricas de precisión de tools.
    Validar no dividir entre 0
    """
    if num_necessary_tools == 0:
        necessary_tools_precision = 1.0
    else:
        necessary_tools_precision = num_called_necessary_tools / num_necessary_tools
    if num_unnecessary_tools == 0:
        unnecessary_tools_precision = 1.0
    else:
        unnecessary_tools_precision = 1 - (num_called_unnecessary_tools / num_unnecessary_tools)
    tool_precision = (necessary_tools_precision + unnecessary_tools_precision) / 2

    return tool_precision, necessary_tools_precision, unnecessary_tools_precision

class ToolPrecisionEvaluator(BaseEvaluator):
    async def evaluate(self, run: Run, example: Example) -> EvaluationResults:
        """
        Evaluador para precisión de llamadas de herramientas.
            -necessary_tool_precision: la cantidad de herramientas necesarias llamadas en relación a las anotadas
            -unnecesary_tool_precision: la cantidad de herramientas no necesarias ignoradas en relación a las anotadas
            -tool_precision: la media de las dos
        """
        output_messages = run.outputs.get("run_state").get("messages")
        necessary_tools = example.outputs.get("necessary_tools")
        unnecessary_tools = example.outputs.get("unnecessary_tools")
        if not output_messages:
            # Si no hay mensajes devolver la por precisión
            print(f"error evaluating agent: not messages found")
            return get_evaluation_result(
                tool_precision=0.0,
                necessary_tool_precision=0.0,
                unnecessary_tool_precision=0.0,
            )
        if not necessary_tools:
            necessary_tools = []
        else:
            necessary_tools = get_list_from_string_comma_separated_values(necessary_tools)
        if not unnecessary_tools:
            unnecessary_tools = []
        else:
            unnecessary_tools = get_list_from_string_comma_separated_values(unnecessary_tools)

        called_tools = []
        for message in output_messages[1:]:
            if message.type == "tool":
                called_tools.append(message.name)

        called_tools = set(called_tools)
        num_necessary_tools = len(necessary_tools)
        num_unnecessary_tools = len(unnecessary_tools)

        num_called_necessary_tools, num_called_unnecessary_tools = get_num_necessary_and_unnecesary_called_tools(called_tools, necessary_tools, unnecessary_tools)

        tool_precision, necessary_tool_precision, unnecessary_tool_precision = calculate_tool_precision(
            num_necessary_tools=num_necessary_tools,
            num_unnecessary_tools=num_unnecessary_tools,
            num_called_unnecessary_tools=num_called_unnecessary_tools,
            num_called_necessary_tools=num_called_necessary_tools
        )

        return get_evaluation_result(
            tool_precision=tool_precision,
            necessary_tool_precision=necessary_tool_precision,
            unnecessary_tool_precision=unnecessary_tool_precision,
        )
