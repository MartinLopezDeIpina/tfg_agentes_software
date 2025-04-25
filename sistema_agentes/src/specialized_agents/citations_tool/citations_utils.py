from typing import List

from langchain_core.messages import BaseMessage, ToolMessage

from src.specialized_agents.citations_tool.models import Citation, CitedAIMessage


def get_citations_from_conversation_messages(messages: List[BaseMessage]) -> List[Citation]:
    citations = []
    for message in messages:
        if isinstance(message, ToolMessage) and message.name=="cite_document":
            try:
                citation = Citation.from_string(message.content)
                if citation:
                    citations.append(citation)
            except Exception as e:
                print(f"Error serializando citación: {e}")
        if isinstance(message, CitedAIMessage):
            try:
                citation = message.citations
                citations.extend(citation)
            except Exception as e:
                print(f"Error obteniendo citación desde mensaje citado: {e}")

    return citations

