from langchain_core.language_models import BaseChatModel
from langchain_mistralai import ChatMistralAI
from langchain_openai import ChatOpenAI


def parse_model(model: str) -> BaseChatModel:
    if model == "gpt-4.1-mini" or model == "gpt-4.1":
        return ChatOpenAI(model=model)
    elif model == "mistral-medium-latest":
        return ChatMistralAI(model=model)