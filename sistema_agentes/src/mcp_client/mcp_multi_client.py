import asyncio
import os
from typing import List, Dict
from contextlib import AsyncExitStack

from langchain_core.tools import BaseTool
from mcp import ClientSession, StdioServerParameters, stdio_client
from mcp.client.sse import sse_client
from langchain_mcp_adapters.tools import load_mcp_tools
from config import REPO_ROOT_ABSOLUTE_PATH
from src.mcp_client.tool_wrapper import patch_tool_with_exception_handling

"""
Se crea un cliente MCP por cada agente. 
Para cada servidor MCP se crea una sesión. Las sesiones pueden ser compartidas entre clientes si más de un cliente se conecta a un servidor.
Un cliente puede conectarse a varias sesiones. 
Cada cliente tiene una lista de tools que filtra desde las disponibles en sus sesiones.
"""

# sesiones con servidores, diccionario de server_id, Session
_global_sessions: Dict[str, ClientSession] = {}
# tools disponibles por cada servidor
_global_tools: Dict[str, BaseTool] = {}
# contexto asíncrono global
_global_exit_stack: AsyncExitStack = None


class MCPClient:
    """Cliente MCP con conexiones compartidas entre instancias"""

    def __init__(self, agent_tools: List[str] = None):
        """
        Solo se cargarán las tools indicadas en agent_tools para pasarle al agente únicamente las tools necesarias.
        Si no se indica ninguna se cargarán todas.
        """
        global _global_exit_stack

        # Inicializar el exit_stack global si no existe
        if _global_exit_stack is None:
            _global_exit_stack = AsyncExitStack()

        self.agent_tools = agent_tools or []
        self.sessions = {}
        self.tools = {}
        self.stdio_transports = {}

    def _check_if_session_exists(self, server_id: str) -> bool:
        """
        Verifica si ya existe una sesión para el servidor especificado.
        Si existe, configura la sesión y tools para este cliente.

        Args:
            server_id: ID del servidor a verificar

        Returns:
            bool: True si la sesión existe y fue configurada, False en caso contrario
        """
        if server_id in _global_sessions:
            self.sessions[server_id] = _global_sessions[server_id]
            self.tools[server_id] = self._filter_tools(server_id)
            return True
        return False

    async def connect_to_gitlab_server(self):
        server_id = "gitlab"

        if self._check_if_session_exists(server_id):
            return

        server_command = "npx"
        server_args = ["-y", "@modelcontextprotocol/server-gitlab"]

        server_env = {
            "GITLAB_PERSONAL_ACCESS_TOKEN": os.getenv('GITLAB_PERSONAL_ACCESS_TOKEN'),
            "GITLAB_API_URL": os.getenv('GITLAB_API_URL'),
        }

        if not server_env["GITLAB_API_URL"]:
            raise ValueError("GITLAB_API_URL is not set in the environment variables.")
        if not server_env["GITLAB_PERSONAL_ACCESS_TOKEN"]:
            raise ValueError("GITLAB_PERSONAL_ACCESS_TOKEN is not set in the environment variables.")

        server_params = StdioServerParameters(
            command=server_command,
            args=server_args,
            env=server_env
        )

        print(f"Connecting to GitLab server with ID {server_id}")
        await self.connect_to_stdio_server(server_id, server_params)

    async def connect_to_google_drive_server(self):
        server_id = "google_drive"

        if self._check_if_session_exists(server_id):
            return

        server_path = f"{REPO_ROOT_ABSOLUTE_PATH}/servidor_mcp_google_drive"

        folder_id = os.getenv('GDRIVE_FOLDER_ID')
        env = {
            "GOOGLE_APPLICATION_CREDENTIALS": f"{server_path}/credentials/gcp-oauth.keys.json",
            "MCP_GDRIVE_CREDENTIALS": f"{server_path}/credentials/.gdrive-server-credentials.json",
            "GDRIVE_FOLDER_ID": folder_id,
        }
        server_script_path = f"{server_path}/index_mod.js"
        server_command = "node"
        server_args = [server_script_path]

        server_params = StdioServerParameters(
            command=server_command,
            args=server_args,
            env=env
        )
        print(f"Connecting to Google Drive server with ID {server_id}")
        await self.connect_to_stdio_server(server_id, server_params)

    async def connect_to_filesystem_server(self):
        server_id = "filesystem"

        if self._check_if_session_exists(server_id):
            return

        docs_path = os.getenv("FILESYSTEM_DOCS_FOLDER")
        if not docs_path:
            raise ValueError("FILESYSTEM_DOCS_FOLDER is not set in the environment variables.")

        server_command = "npx"
        server_args = ["-y", "@modelcontextprotocol/server-filesystem", docs_path]

        server_params = StdioServerParameters(
            command=server_command,
            args=server_args,
            env={}
        )

        print(f"Connecting to filesystem server with ID {server_id}")
        await self.connect_to_stdio_server(server_id, server_params)

    async def connect_to_stdio_server(self, server_id: str, stdio_params: StdioServerParameters):
        """Conectar a un servidor MCP usando stdio."""
        global _global_sessions, _global_tools, _global_exit_stack

        if self._check_if_session_exists(server_id):
            return

        # Establecer la conexión usando el exit_stack global
        stdio_transport = await _global_exit_stack.enter_async_context(stdio_client(stdio_params))
        self.stdio_transports[server_id] = stdio_transport
        stdio, write = stdio_transport

        # Crear la sesión
        session = await _global_exit_stack.enter_async_context(ClientSession(stdio, write))

        # Guardar la sesión a nivel global y en la instancia actual
        _global_sessions[server_id] = session
        self.sessions[server_id] = session

        # Inicializar la sesión y cargar herramientas
        await self._initialize_session(server_id)

    async def connect_to_sse_server(self, host_ip: str, host_port: int):
        """Conectar a un servidor MCP usando SSE."""
        global _global_sessions, _global_tools, _global_exit_stack

        server_id = f"{host_ip}:{host_port}"

        if self._check_if_session_exists(server_id):
            return

        print(f"Connecting to SSE server at {host_ip}:{host_port}")

        # Usar el exit_stack global
        streams = await _global_exit_stack.enter_async_context(
            sse_client(f"http://{host_ip}:{host_port}/sse")
        )

        session = await _global_exit_stack.enter_async_context(
            ClientSession(streams[0], streams[1])
        )

        # Guardar la sesión a nivel global y en la instancia actual
        _global_sessions[server_id] = session
        self.sessions[server_id] = session

        # Inicializar la sesión y cargar herramientas
        await self._initialize_session(server_id)

    async def _initialize_session(self, server_id: str):
        """Inicializa una sesión y carga sus herramientas."""
        global _global_tools

        await self.sessions[server_id].initialize()

        # Cargar herramientas de langchain solo si no se han cargado antes
        if server_id not in _global_tools:
            tools = await load_mcp_tools(self.sessions[server_id])
            wrapped_tools = [patch_tool_with_exception_handling(tool) for tool in tools]
            _global_tools[server_id] = wrapped_tools

        # Filtrar herramientas para este cliente
        self.tools[server_id] = self._filter_tools(server_id)

        # Listar herramientas disponibles para debug
        print(f"\nConectado al servidor {server_id} con herramientas:",
              [tool.name for tool in self.tools[server_id]])

    def _filter_tools(self, server_id: str) -> List[BaseTool]:
        """Filtrar herramientas según la lista agent_tools"""
        global _global_tools

        if server_id not in _global_tools:
            return []

        if not self.agent_tools:
            return _global_tools[server_id]

        return [tool for tool in _global_tools[server_id]
                if tool.name in self.agent_tools]

    async def call_tool(self, server_id: str, tool_name: str, tool_args: dict):
        if server_id not in self.sessions:
            raise ValueError(f"No hay conexión con el servidor ID {server_id}")

        result = await self.sessions[server_id].call_tool(tool_name, tool_args)
        return result

    def get_tools(self) -> List[BaseTool]:
        all_tools = []
        for tools in self.tools.values():
            all_tools.extend(tools)
        return all_tools

    def get_specific_server_tools(self, server_id: str) -> List[BaseTool]:
        if server_id not in self.tools:
            raise ValueError(f"No hay herramientas para el servidor ID {server_id}")
        return self.tools[server_id]

    def get_all_server_ids(self) -> List[str]:
        return list(self.sessions.keys())

    @staticmethod
    async def cleanup():
        """Desconecta de todos los servidores cerrando el exit_stack global."""
        global _global_exit_stack, _global_sessions, _global_tools

        try:
            if _global_exit_stack:
                await _global_exit_stack.aclose()
                _global_exit_stack = None
                _global_sessions = {}
                _global_tools = {}
                print("Todos los servidores desconectados correctamente")
        except Exception as e:
            print(f"Error durante la limpieza global: {e}")