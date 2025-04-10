import asyncio
from dotenv import load_dotenv

from src.agente_react_prebuilt import ejecutar_agente_codigo, execute_confluence_agent

if __name__ == '__main__':
    load_dotenv()

    #asyncio.run(ejecutar_agente_codigo("Qué es lo que explica cada notebook de jupyter?"))

    #asyncio.run(execute_confluence_agent("Existe alguna guía de estilos para el proyecto?, si es así, qué color primario se utiliza?"))
    asyncio.run(execute_confluence_agent("Qué funcionalidades tiene el frontend?"))