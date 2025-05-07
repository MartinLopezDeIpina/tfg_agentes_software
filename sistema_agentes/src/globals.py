from contextlib import AsyncExitStack
from typing import Dict

from langchain_core.tools import BaseTool
from mcp import ClientSession

# contexto asíncrono global
global_exit_stack: AsyncExitStack = AsyncExitStack()

