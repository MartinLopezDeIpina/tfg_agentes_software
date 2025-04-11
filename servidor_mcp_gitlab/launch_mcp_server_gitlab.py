#!/usr/bin/env python3
"""
Script para lanzar un servidor MCP para Atlassian utilizando uvx con transporte SSE.
"""

import os
import subprocess
import sys
from dotenv import load_dotenv
import argparse


def main():
    load_dotenv()

    gitlab_api_token = os.getenv('GITLAB_API_TOKEN')
    gitlab_api_url = os.getenv('GITLAB_API_URL')

    mcp_transport = os.getenv('MCP_TRANSPORT') or 'sse'
    mcp_port = os.getenv('MCP_PORT') or '9000'

    # Si no hay configuración mínima, mostrar error
    if not gitlab_api_url:
        print("Error: CONFLUENCE_URL no está configurada. Por favor, configure el archivo .env")
        sys.exit(1)
    if not gitlab_api_url:
        print("Error: CONFLUENCE_USERNAME no está configurada. Por favor, configure el archivo .env")
        sys.exit(1)

    # Construir el comando base para npx
    command = ["npx", "-y", "@modelcontextprotocol/server-gitlab"]

    if mcp_transport:
        command.extend(["--transport", mcp_transport])
    if mcp_port:
        command.extend(["--port", mcp_port])

    # Configurar variables de entorno
    env = {
        "GITLAB_PERSONAL_ACCESS_TOKEN": gitlab_api_token,
        "GITLAB_API_URL": gitlab_api_url
    }

    # Ejecutar el comando
    try:
        print(f"Ejecutando: {' '.join(command)}")
        # Pasar las variables de entorno al proceso
        subprocess.run(command, env={**os.environ, **env})
    except KeyboardInterrupt:
        print("\nServidor detenido por el usuario")
    except Exception as e:
        print(f"Error al ejecutar el servidor: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
