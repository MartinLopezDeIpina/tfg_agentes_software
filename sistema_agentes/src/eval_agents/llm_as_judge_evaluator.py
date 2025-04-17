from langchain_openai import ChatOpenAI
from langsmith import EvaluationResult
from langsmith.schemas import Example, Run
from pydantic import StrictFloat

from src.eval_agents.models import JudgeLLMResponse
from src.utils import get_list_from_string_comma_separated_values, get_list_string_with_indexes
from static.prompts import LLM_JUDGE_PROMPT


async def llm_as_a_judge(run: Run, example: Example) -> EvaluationResult:
    """
    Evaluador para determinar si las respuestas de los agentes son correctas.
    Un agente llm-judge determina si la respuesta es correcta partiendo de la instancia del dataset con la solución anotada.
    La solución son "conceptos" que la respuesta del agente debe contener.
    """

    run_result = run.outputs.get("result")
    run_solution = example.outputs.get("solution")
    solution_list = get_list_from_string_comma_separated_values(run_solution)
    
    model = ChatOpenAI(model="gpt-4o-mini")
    structured_llm = model.with_structured_output(JudgeLLMResponse)


    try:
        ground_truth_list = get_list_string_with_indexes(solution_list)
        model_evaluation = await structured_llm.ainvoke(
            input=LLM_JUDGE_PROMPT.format(
                ground_truth=ground_truth_list,
                generated_solution=run_result,
                query=run.outputs.get("run_state").get("query")
            )
        )
        if not isinstance(ground_truth_list, JudgeLLMResponse):
            model_evaluation = JudgeLLMResponse.model_validate(model_evaluation)


        right_concepts = len([elem for elem in model_evaluation.corrections if elem.is_included])
        solution_len = len(solution_list)
        score = right_concepts / solution_len if len(solution_list) > 0 else 0.0

        return EvaluationResult(
            key="llm-as-a-judge",
            score=StrictFloat(score)
        )

    except Exception as e:
        print(f"error evaluating: {e}")
        return EvaluationResult.FAILED


    




