import os
from dotenv import load_dotenv
load_dotenv()

MCP_CODE_SERVER_DIR = os.environ.get("MCP_CODE_SERVER_DIR")
MCP_CODE_SERVER_PORT = os.environ.get("MCP_CODE_SERVER_PORT")

REPO_ROOT_ABSOLUTE_PATH = "/home/martin/tfg_agentes_software"
