from typing import List, Sequence
from mcp.types import Tool
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool


class MCPAgent:

    def __init__(self, tools: List[Tool] | List[BaseTool]):
        self.tools = tools

    def ejecutar_agente(self):
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.5,
            max_tokens=2000,
            timeout=None,
            max_retries=2,
        )
        input = "retrieve useful documents for the query: \"What is the capital of France?\""
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "you are a helpful assistant that answers questions about a data base.",
                ),
                ("human", "{input}"),
            ]
        )

        llm_with_tools = llm.bind_tools(self.tools)

        chain = prompt | llm_with_tools

        return chain.invoke(input)


