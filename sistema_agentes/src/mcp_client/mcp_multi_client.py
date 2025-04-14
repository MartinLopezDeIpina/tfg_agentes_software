import asyncio
import copy
import types
import uuid
from functools import wraps

from dotenv import load_dotenv
import json
import os
from typing import Optional, List, Dict
from contextlib import AsyncExitStack

from langchain_core.messages import ToolMessage

from config import REPO_ROOT_ABSOLUTE_PATH

from langchain_core.tools import BaseTool
from mcp import ClientSession, StdioServerParameters, stdio_client
from mcp.client.sse import sse_client
from mcp.types import Tool
from langchain_mcp_adapters.tools import load_mcp_tools
from config import MCP_CODE_SERVER_DIR, MCP_CODE_SERVER_PORT
from src.mcp_client.tool_wrapper import patch_tool_with_exception_handling


class SharedExitStack(AsyncExitStack):
    """AsyncExitStack compartido como singleton"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SharedExitStack, cls).__new__(cls)
            AsyncExitStack.__init__(cls._instance)
        return cls._instance

    @classmethod
    async def cleanup_all(cls):
        """Cierra todos los recursos del exit_stack compartido"""
        if cls._instance:
            try:
                await cls._instance.aclose()
            except Exception as e:
                print(f"Error durante la limpieza global: {e}")
            finally:
                cls._instance = None

class MCPClient:
    """Cliente MCP con capacidad para múltiples conexiones STDIO o SSE, gestionadas con un único exit_stack"""

    def __init__(self, agent_tools: List[str] = None):
        """
        Solo se cargarán las tools indicadas en agent_tools para pasarle al agente unicamente las tools necesarias.
        Si no se indica ninguna se cargarán todas.
        """
        if not agent_tools:
            agent_tools = []

        self.sessions: Dict[str, ClientSession] = {}
        self.tools: Dict[str, List[BaseTool]] = {}
        self.agent_tools = agent_tools
        self.stdio_transports: Dict[str, tuple] = {}
        self.exit_stack = SharedExitStack()

    async def connect_to_gitlab_server(self):
        server_id = "gitlab"

        if server_id in self.sessions:
            print(f"Ya existe una conexión con ID {server_id}. Usando un ID diferente o cierra la conexión primero.")
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

        if server_id in self.sessions:
            print(f"Ya existe una conexión con ID {server_id}. Usando un ID diferente o cierra la conexión primero.")
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

        if server_id in self.sessions:
            print(f"Ya existe una conexión con ID {server_id}. Usando un ID diferente o cierra la conexión primero.")
            return

        # Establecer la conexión usando el exit_stack único
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(stdio_params))
        self.stdio_transports[server_id] = stdio_transport
        stdio, write = stdio_transport

        # Crear la sesión
        self.sessions[server_id] = await self.exit_stack.enter_async_context(ClientSession(stdio, write))

        # Inicializar la sesión y cargar herramientas
        await self.initialize_session(server_id)

    async def connect_to_sse_server(self, host_ip: str, host_port: int):
        """Conectar a un servidor MCP usando SSE."""

        server_id = f"{host_ip}:{host_port}"
        if server_id in self.sessions:
            print(f"Ya existe una conexión con ID {server_id}. Usando un ID diferente o cierra la conexión primero.")
            return

        print(f"Connecting to SSE server at {host_ip}:{host_port}")

        # Usar el exit_stack único
        streams = await self.exit_stack.enter_async_context(
            sse_client(f"http://{host_ip}:{host_port}/sse")
        )

        self.sessions[server_id] = await self.exit_stack.enter_async_context(
            ClientSession(streams[0], streams[1])
        )

        await self.initialize_session(server_id)

    async def initialize_session(self, server_id: str):
        """Inicializa una sesión y carga sus herramientas."""

        await self.sessions[server_id].initialize()

        # Cargar herramientas de langchain
        tools = await load_mcp_tools(self.sessions[server_id])
        wrapped_tools = [patch_tool_with_exception_handling(tool) for tool in tools]
        if len(self.agent_tools) == 0:
            self.tools[server_id] = wrapped_tools
        else:
            self.tools[server_id] = [tool for tool in wrapped_tools if tool.name in self.agent_tools]

        # Listar herramientas disponibles para debug
        print(f"\nConectado al servidor {server_id} con herramientas:", [tool.name for tool in tools])

        for tool in tools:
            print(f"Tool: {tool.name}, schema: {tool.input_schema}")

    async def call_tool(self, server_id: str, tool_name: str, tool_args: dict):

        if server_id not in self.sessions:
            raise ValueError(f"No hay conexión con el servidor ID {server_id}")

        result = await self.sessions[server_id].call_tool(tool_name, tool_args)
        return result

    def get_tools(self) -> List[BaseTool]:
        all_tools = []
        for server_id, tools in self.tools.items():
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
        """Desconecta de todos los servidores cerrando el único exit_stack."""
        try:
            # Cerrar todos los recursos con una sola operación
            await SharedExitStack.cleanup_all()
            print("Todos los servidores desconectados correctamente")
        except Exception as e:
            print(f"Error durante la limpieza global: {e}")

async def main():
    load_dotenv()
    client = MCPClient()
    client2 = MCPClient()

    try:
        await client.connect_to_filesystem_server()
        await client2.connect_to_google_drive_server()
    except Exception as e:
        print(f"Error: {e}")

    finally:
        await MCPClient.cleanup()

if __name__ == "__main__":
    asyncio.run(main())