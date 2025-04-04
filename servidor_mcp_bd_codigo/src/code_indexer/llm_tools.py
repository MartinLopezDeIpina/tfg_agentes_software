from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
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

class AsyncEmbedder:
    model: str
    embedder_instance: OpenAIEmbeddings

    def __init__(self, model: str = "text-embedding-3-small", embedder_instance: OpenAIEmbeddings = None):
        self.model = model
        if embedder_instance is None:
            self.embedder_instance = OpenAIEmbeddings(
                model=model
            )

    async def async_embed_document(self, document: str):
        embedding = await self.embedder_instance.aembed_query(document)
        return embedding
