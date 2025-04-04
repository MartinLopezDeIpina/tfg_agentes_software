from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
from config import LLM_TEMPERATURE
from langchain_core.messages import BaseMessage
from typing import List

class AsyncLLMPrompter:
    model: str
    llm_chat: BaseChatModel

    def __init__(self, model: str = "gpt-4o-mini", llm_chat: BaseChatModel = None):
        self.model = model
        if llm_chat is None:
            self.llm_chat = ChatOpenAI(
                model=model,
                temperature=LLM_TEMPERATURE
            )

    async def async_execute_prompt(self, prompt_messages: List[BaseMessage]):
        response = await self.llm_chat.ainvoke(prompt_messages)
        return response

