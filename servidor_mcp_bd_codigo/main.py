import asyncio

from src.db_connection import DBConnection
from src.mcp_client import MCPClient
from dotenv import load_dotenv
from src.agente_prueba import MCPAgent
from src.pg_vector_tools import PGVectorTools


async def run_db_agent():
    mcp_client = MCPClient()
    try:
        await mcp_client.connect_to_server()

        tools = mcp_client.get_tools()
        mcp_agent = MCPAgent(tools)
        resultado = mcp_agent.ejecutar_agente()
        print(f"resultado: {resultado}")
    finally:
        await mcp_client.cleanup()


if __name__ == '__main__':
    load_dotenv()

    asyncio.run(run_db_agent())




