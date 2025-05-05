import asyncio
import os
from typing import List, Dict

from langchain_core.tools import BaseTool
from mcp import ClientSession, StdioServerParameters, stdio_client
from mcp.client.sse import sse_client
from langchain_mcp_adapters.tools import load_mcp_tools
from config import GITLAB_API_URL

from config import REPO_ROOT_ABSOLUTE_PATH
from src.mcp_client.tool_wrapper import patch_tool_with_exception_handling
from src.globals import global_exit_stack

"""
Se crea un cliente MCP con una instancia singleton, cada agente guarda un puntero a la instancia. 
Para cada servidor MCP se crea una sesión. Las sesiones pueden ser compartidas entre clientes si más de un cliente se conecta a un servidor.
Un cliente puede conectarse a varias sesiones. 
Se guarda una lista de nombres de tools para cada agente. Cuando se solicitan las tools de un agente, se filtran desde todas las tools disponibles.
"""
class MCPClient:
    _instance = None

    # sesiones con servidores, diccionario de server_id, Session
    _sessions: Dict[str, ClientSession] = {}
    # tools disponibles por cada servidor
    _tools: Dict[str, List[BaseTool]] = {}
    # Nombres de las tools requeridas por cada agente
    _agent_tools: Dict[str, List[str]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MCPClient, cls).__new__(cls)
            cls._instance._sessions = {}
            cls._instance._tools = {}
            cls._instance._agent_tools = {}
            cls._instance.stdio_transports = {}
        return cls._instance

    @classmethod
    def get_instance(cls):
        return cls._instance or cls()

    def register_agent(self, agent_name: str, tools: List[str]):
        self._agent_tools[agent_name] = tools

    def _check_if_session_exists(self, server_id: str) -> bool:
        if server_id in self._sessions:
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
            "GITLAB_API_URL": GITLAB_API_URL
        }

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
        if self._check_if_session_exists(server_id):
            return

        # Establecer la conexión usando el exit_stack global
        stdio_transport = await global_exit_stack.enter_async_context(stdio_client(stdio_params))
        stdio, write = stdio_transport

        # Crear la sesión
        session = await global_exit_stack.enter_async_context(ClientSession(stdio, write))
        self._sessions[server_id] = session

        # Inicializar la sesión y cargar herramientas
        await self._initialize_session(server_id)

    async def connect_to_confluence_server(self):
        server_id = "confluence"
        host=os.getenv('CONFLUENCE_HOST')
        port=os.getenv('CONFLUENCE_PORT')

        if not host or not port:
            raise ValueError("CONFLUENCE_HOST or CONFLUENCE_PORT is not set in the environment variables.")
        port = int(port)

        await self.connect_to_sse_server(server_id, host, port)
        
    async def connect_to_code_server(self):
        server_id = "code_repo"
        host=os.getenv('MCP_CODE_SERVER_HOST')
        port=os.getenv('MCP_CODE_SERVER_PORT')

        if not host or not port:
            raise ValueError("MCP_CODE_SERVER_HOST or MCP_CODE_SERVER_PORT is not set in the environment variables.")
        port = int(port)

        await self.connect_to_sse_server(server_id, host, port)

    async def connect_to_sse_server(self, server_id: str, host_ip: str, host_port: int):
        """Conectar a un servidor MCP usando SSE."""
        if self._check_if_session_exists(server_id):
            return

        print(f"Connecting to SSE server at {host_ip}:{host_port}")

        # Usar el exit_stack global
        streams = await global_exit_stack.enter_async_context(
            sse_client(f"http://{host_ip}:{host_port}/sse")
        )

        session = await global_exit_stack.enter_async_context(
            ClientSession(streams[0], streams[1])
        )
        self._sessions[server_id] = session

        # Inicializar la sesión y cargar herramientas
        await self._initialize_session(server_id)

    async def _initialize_session(self, server_id: str):
        """Inicializa una sesión y carga sus herramientas."""
        await self._sessions[server_id].initialize()

        # Cargar herramientas de langchain solo si no se han cargado antes
        if server_id not in self._tools:
            tools = await load_mcp_tools(self._sessions[server_id])
            wrapped_tools = [patch_tool_with_exception_handling(tool) for tool in tools]
            self._tools[server_id] = wrapped_tools

        # Listar herramientas disponibles para debug
        print(f"\nConectado al servidor {server_id} con herramientas:",
              [tool.name for tool in self._tools[server_id]])

    async def call_tool(self, server_id: str, tool_name: str, tool_args: dict):
        if server_id not in self._sessions:
            raise ValueError(f"No hay conexión con el servidor ID {server_id}")

        result = await self._sessions[server_id].call_tool(tool_name, tool_args)
        return result

    def get_agent_tools(self, agent_name: str) -> List[BaseTool]:
        """Obtiene todas las herramientas disponibles para un agente específico."""
        if agent_name not in self._agent_tools:
            return []

        requested_tool_names = self._agent_tools[agent_name]
        all_tools = []
        # Iterar por todos los servidores para encontrar herramientas coincidentes
        for server_id, server_tools in self._tools.items():
            matching_tools = [tool for tool in server_tools if tool.name in requested_tool_names]
            all_tools.extend(matching_tools)

        return all_tools

    def get_specific_server_tools(self, server_id: str) -> List[BaseTool]:
        if server_id not in self._tools:
            raise ValueError(f"No hay herramientas para el servidor ID {server_id}")
        return self._tools[server_id]

    def get_all_server_ids(self) -> List[str]:
        return list(self._sessions.keys())

    @staticmethod
    async def cleanup():
        """Desconecta de todos los servidores cerrando el exit_stack global."""
        try:
            if global_exit_stack:
                await global_exit_stack.aclose()
                print("Todos los servidores desconectados correctamente")
        except Exception as e:
            print(f"Error durante la limpieza global: {e}")

async def main():
    mcp_client = MCPClient()
    await mcp_client.connect_to_code_server()
    
    tool_name = "get_code_repository_rag_docs_from_query_tool"
    tool_args = {
        "query": "¿Se utiliza algún patrón o metodología para crear alguna clase?"
    }

    result = await mcp_client.call_tool(server_id="code_repo", tool_name=tool_name, tool_args=tool_args)
    tree = await mcp_client.call_tool(server_id="code_repo", tool_name="get_repository_tree_tool", tool_args={})
    print(tree)
    print(result)

    await MCPClient.cleanup()



if __name__ == "__main__":
    asyncio.run(main())















