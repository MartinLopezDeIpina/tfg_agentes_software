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

    confluence_url = os.getenv('CONFLUENCE_URL')
    confluence_username = os.getenv('CONFLUENCE_USERNAME')
    confluence_token = os.getenv('CONFLUENCE_TOKEN')
    mcp_transport = os.getenv('MCP_TRANSPORT') or 'sse'
    mcp_port = os.getenv('MCP_PORT') or '9000'

    # Si no hay configuración mínima, mostrar error
    if not confluence_url:
        print("Error: CONFLUENCE_URL no está configurada. Por favor, configure el archivo .env")
        sys.exit(1)
    if not confluence_username:
        print("Error: CONFLUENCE_USERNAME no está configurada. Por favor, configure el archivo .env")
        sys.exit(1)
    if not confluence_token:
        print("Error: CONFLUENCE_TOKEN no está configurada. Por favor, configure el archivo .env")
        sys.exit(1)

    # Construir el comando base para uvx
    command = ["uvx", "mcp-atlassian"]
    
    command.extend(["--transport", mcp_transport])
    command.extend(["--port", mcp_port]) 
    command.extend(["--confluence-url", confluence_url])
    command.extend(["--confluence-username", confluence_username])
    command.extend(["--confluence-token", confluence_token])

    # Ejecutar el comando
    try:
        print(f"Ejecutando: {' '.join(command)}")
        subprocess.run(command)
    except KeyboardInterrupt:
        print("\nServidor detenido por el usuario")
    except Exception as e:
        print(f"Error al ejecutar el servidor: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
