from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI
#from langchain_community.embeddings import OpenAIEmbeddings
from langchain_openai import OpenAIEmbeddings
from config import LLM_TEMPERATURE
from langchain_core.messages import BaseMessage
from typing import List
from config import EMBEDDER_MODEL_INSTANCE


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

    def __init__(self, model: str = "text-embedding-3-small", embedder_instance: OpenAIEmbeddings = EMBEDDER_MODEL_INSTANCE):
        self.model = model
        self.embedder_instance = embedder_instance

    async def async_embed_document(self, document: str):
        embedding = await self.embedder_instance.aembed_query(document)
        return embedding
