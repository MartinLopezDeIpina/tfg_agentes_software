import asyncio
from dotenv import load_dotenv

from src.code_agent.agente_react_prebuilt import ejecutar_agente_codigo

if __name__ == '__main__':
    load_dotenv()

    asyncio.run(ejecutar_agente_codigo("Qué es lo que explica cada notebook de jupyter?"))