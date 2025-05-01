from contextlib import AsyncExitStack
from typing import Dict

from langchain_core.tools import BaseTool
from mcp import ClientSession

# sesiones con servidores, diccionario de server_id, Session
global_sessions: Dict[str, ClientSession] = {}
# tools disponibles por cada servidor
global_tools: Dict[str, BaseTool] = {}
# contexto asíncrono global
global_exit_stack: AsyncExitStack = AsyncExitStack()

