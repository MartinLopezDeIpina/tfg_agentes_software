import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

MCP_CODE_SERVER_DIR = os.environ.get("MCP_CODE_SERVER_DIR")
MCP_CODE_SERVER_PORT = os.environ.get("MCP_CODE_SERVER_PORT")

REPO_ROOT_ABSOLUTE_PATH = "/home/martin/tfg_agentes_software"
CSV_DATASET_RELATIVE_PATH = "static/evaluation_dataset.csv"
GRAPH_IMAGES_RELATIVE_PATH = "static/images"

default_llm = ChatOpenAI(
    model="gpt-4o-mini"
)
default_reasoner_llm = ChatOpenAI(
    model="o3-mini"
)

