import asyncio
import json
from abc import ABC
from typing import TypedDict, List

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage

from src.BaseAgent import AgentState
from src.mcp_client.mcp_multi_client import MCPClient
from src.specialized_agents.SpecializedAgent import SpecializedAgent
from src.specialized_agents.citations_tool.models import ConfluenceDataSource
from src.utils import tab_all_lines_x_times
from static.agent_descriptions import CONFLUENCE_AGENT_DESCRIPTION
from static.prompts import CITE_REFERENCES_PROMPT, confluence_system_prompt, cached_confluence_system_prompt


class BaseConfluenceAgent(SpecializedAgent, ABC):
    def __init__(self, prompt: str, model: BaseChatModel = None, prompt_only_tools: List[str] = None):
        super().__init__(
            name="confluence_agent",
            description=CONFLUENCE_AGENT_DESCRIPTION,
            model=model,
            tools_str= [
                "confluence_search",
                "confluence_get_page"
            ],
            prompt_only_tools=prompt_only_tools or [],
            data_sources=[ConfluenceDataSource(
                get_documents_tool_name="confluence_search",
                tools_args= {
                    "query":"type=page",
                    "limit": 50
                }
            )],
            prompt=CITE_REFERENCES_PROMPT.format(
                agent_prompt=prompt
            )
        )

    async def connect_to_mcp(self):
        self.mcp_client = MCPClient.get_instance()
        await self.mcp_client.connect_to_confluence_server()

        self.mcp_client.register_agent(self.name, self.tools_str)
        self.tools = self.mcp_client.get_agent_tools(self.name)


class ConfluenceAgent(BaseConfluenceAgent):
    def __init__(self, model: BaseChatModel = None, ):
        super().__init__(prompt=confluence_system_prompt, prompt_only_tools=[], model=model)

    async def prepare_prompt(self, state: AgentState) -> AgentState:
        pages_tool = None
        for tool in self.tools:
            if tool.name == "confluence_search":
                pages_tool = tool

        pages_task = pages_tool.ainvoke({
            "query":"type=page",
            "limit": 50
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
                self.prompt.format(
                    confluence_pages_preview=confluence_pages_preview,
                )
            ),
            HumanMessage(
                content=state["query"]
            )
        ]
        state["messages"] = messages
        return state

class CachedConfluenceAgent(BaseConfluenceAgent):
    def __init__(self, model: BaseChatModel = None):
        super().__init__(
            prompt=cached_confluence_system_prompt,
            prompt_only_tools=[
                "confluence_search",
                "confluence_get_page"
            ],
            model=model
        )

    async def prepare_prompt(self, state: AgentState) -> AgentState:
        get_page_tool = None
        search_tool = None
        for tool in self.tools:
            if tool.name == "confluence_search":
                search_tool = tool
            if tool.name == "confluence_get_page":
                get_page_tool = tool

        pages_result = await search_tool.ainvoke({
            "query":"type=page",
            "limit": 50
        })
        pages = json.loads(pages_result)
        get_pages_tasks = []
        for page in pages:
            get_pages_tasks.append(
                get_page_tool.ainvoke({
                    "page_id": page.get("id")
                })
            )
        pages_call = await asyncio.gather(*get_pages_tasks)
        pages_list = [json.loads(page) for page in pages_call]

        pages_information = []
        for i, page in enumerate(pages_list):
            try:
                page = page["metadata"]
                title = page["title"]
                id = page["id"]
                content = tab_all_lines_x_times(page["content"]["value"])
                pages_information.append(f"{i}. id: {id}, title: {title}\n{content}")
            except Exception as e:
                print(f"Error procesando página Confluence: {e}")

        confluence_pages_preview = "\n\n".join(pages_information)
        confluence_pages_preview = tab_all_lines_x_times(confluence_pages_preview)

        messages = [
            SystemMessage(
                self.prompt.format(
                    confluence_pages_preview=confluence_pages_preview,
                )
            ),
            HumanMessage(
                content=state["query"]
            )
        ]
        state["messages"] = messages
        return state
