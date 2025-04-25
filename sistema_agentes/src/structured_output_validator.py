from typing import Type, Optional, Sequence
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain.output_parsers import RetryOutputParser
from pydantic import BaseModel
from config import default_llm

async def execute_structured_llm_with_validator_handling(
    prompt: str | Sequence[BaseMessage],
    output_schema: Type[BaseModel],
    max_retries: int = 2,
    llm: BaseChatModel = default_llm,
) -> BaseModel:
    """
    Ejecuta el structured_output_llm y si no responde con el modelo requerido intenta parsearlo con otro modelo.
    Si no se recibe una respuesta se vuelve a intentar.
    Si lo intenta el máximo de intentos y no lo consigue lanza la excepción para manejarla en el agente.
    """

    structured_model = llm.with_structured_output(output_schema)
    parser = PydanticOutputParser(pydantic_object=output_schema)
    retry_parser = RetryOutputParser.from_llm(parser=parser, llm=default_llm)

    last_exception: Optional[Exception] = None
    raw_response: Optional[str] = None

    for _ in range(max_retries):
        try:
            response = await structured_model.ainvoke(prompt)
            raw_response = response if isinstance(response, str) else None

            if not isinstance(response, output_schema):
                response = output_schema.model_validate(response)
            return response

        except Exception as e:
            last_exception = e
            if raw_response is not None:
                try:
                    response = retry_parser.parse(raw_response)
                    if not isinstance(response, output_schema):
                        response = output_schema.model_validate(response)
                    return response
                except Exception as retry_e:
                    last_exception = retry_e

    # Si se intenta varias veces y no se consigue lanzar la excepción
    raise last_exception
