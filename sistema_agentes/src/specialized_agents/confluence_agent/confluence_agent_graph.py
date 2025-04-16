import asyncio
import json
from typing import TypedDict, List

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage

from src.mcp_client.mcp_multi_client import MCPClient
from src.specialized_agents.SpecializedAgent import SpecializedAgent
from src.specialized_agents.confluence_agent.prompts import system_prompt
from src.utils import tab_all_lines_x_times
from static.agent_descriptions import CONFLUENCE_AGENT_DESCRIPTION


class ConfluenceAgent(SpecializedAgent):
    def __init__(self, model: BaseChatModel = None):
        super().__init__(
            name="confluence_agent",
            description=CONFLUENCE_AGENT_DESCRIPTION,
            model=model,
            tools_str= [
                "confluence_search",
                "confluence_get_page"
            ]
        )

    async def connect_to_mcp(self):
        self.mcp_client = MCPClient(agent_tools=self.tools_str)
        await self.mcp_client.connect_to_confluence_server()
        self.tools = self.mcp_client.get_tools()

    async def prepare_prompt(self, query: str) -> List[BaseMessage]:
        pages_tool = None
        for tool in self.tools:
            if tool.name == "confluence_search":
                pages_tool = tool

        pages_task = pages_tool.ainvoke({
            "query":"type=page",
            "limit": 500
        })

        pages_result = await asyncio.gather(pages_task)
        pages = json.loads(pages_result[0])
        pages_titles = []
        for i, page in enumerate(pages):
            # Si no tiene titulo añadir toda la página
            try:
                title = page["title"]
                id = page["id"]
                pages_titles.append(f"{i}. id: {id}, title: {title}")
            except Exception:
                pages_titles.append(page)

        confluence_pages_preview = "\n".join(pages_titles)
        confluence_pages_preview = tab_all_lines_x_times(confluence_pages_preview)

        messages = [
            SystemMessage(
                system_prompt.format(
                    confluence_pages_preview=confluence_pages_preview
                ),
            ),
            HumanMessage(
                content=query
            )
        ]
        return messages
