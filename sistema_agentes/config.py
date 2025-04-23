import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

MCP_CODE_SERVER_DIR = os.environ.get("MCP_CODE_SERVER_DIR")
MCP_CODE_SERVER_PORT = os.environ.get("MCP_CODE_SERVER_PORT")

REPO_ROOT_ABSOLUTE_PATH = "/home/martin/tfg_agentes_software"

CSV_DATASET_RELATIVE_PATH = "static/evaluation_dataset.csv"
CSV_DATASET_PRUEBA_RELATIVE_PATH = "static/evaluation_dataset_prueba.csv"

GRAPH_IMAGES_RELATIVE_PATH = "static/images"
OFICIAL_DOCS_RELATIVE_PATH = "/sistema_agentes/static/gen_docs"

CODE_REPO_ROOT_ABSOLUTE_PATH = "/home/martin/open_source/ia-core-tools"

GITLAB_API_URL="https://gitlab.devops.lksnext.com/api/v4"
GITLAB_PROJECT_URL=1141
GITLAB_PROJECT_NORMAL_URL="https://gitlab.devops.lksnext.com/lks/genai/ia-core-tools"

default_llm = ChatOpenAI(
    model="gpt-4.1-mini"
)
default_reasoner_llm = ChatOpenAI(
    model="o4-mini"
)

