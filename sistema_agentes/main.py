import asyncio
from dotenv import load_dotenv

from src.agente_react_prebuilt import ejecutar_agente_codigo, execute_confluence_agent, execute_gitlab_agent, \
    execute_google_drive_agent, execute_filesystem_agent

if __name__ == '__main__':
    load_dotenv()

    #asyncio.run(ejecutar_agente_codigo("Qué es lo que explica cada notebook de jupyter?"))

    #asyncio.run(execute_confluence_agent("Existe alguna guía de estilos para el proyecto?, si es así, qué color primario se utiliza?"))
    #asyncio.run(execute_confluence_agent("Qué funcionalidades tiene el frontend?"))
    #asyncio.run(execute_gitlab_agent("Qué ramas existen en el proyecto?"))
    #asyncio.run(execute_google_drive_agent("Existe alguna maqueta para la gestión del administrador?"))
    asyncio.run(execute_filesystem_agent("Existe alguna maqueta para la gestión del administrador?"))
