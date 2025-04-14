import asyncio
from typing import TypedDict, List
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from src.mcp_client.mcp_multi_client import MCPClient
from static.agent_descriptions import CODE_AGENT_DESCRIPTION

from src.specialized_agents.BaseAgent import BaseAgent
from src.specialized_agents.code_agent.prompts import system_prompt

class CodeAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="code_agent",
            description=CODE_AGENT_DESCRIPTION,
            model=ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0,
            ),
            tools_str= [
                "get_code_repository_rag_docs_from_query_tool",
                "get_file_from_repository_tool",
                "get_repository_tree_tool",
            ]
        )

    async def connect_to_mcp(self):
        self.mcp_client = MCPClient(agent_tools=self.tools_str)
        await self.mcp_client.connect_to_code_server()
        self.tools = self.mcp_client.get_tools()

    async def prepare_prompt(self, query: str) -> List[BaseMessage]:
        rag_tool = None
        tree_tool = None
        for tool in self.tools:
            if tool.name == "get_code_repository_rag_docs_from_query_tool":
                rag_tool = tool
            elif tool.name == "get_repository_tree_tool":
                tree_tool = tool

        tree_task = tree_tool.ainvoke({})
        rag_task = rag_tool.ainvoke({
            "query": query
        })

        proyect_tree, initial_retrieved_docs = await asyncio.gather(tree_task, rag_task)

        messages = [
            SystemMessage(
                system_prompt.format(
                    proyect_tree=proyect_tree,
                    initial_retrieved_docs=initial_retrieved_docs
                )
            ),
            HumanMessage(
                content=query
            )

        ]
        return messages
