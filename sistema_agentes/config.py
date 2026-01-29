import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_mistralai import ChatMistralAI

load_dotenv()

MCP_CODE_SERVER_DIR = os.environ.get("MCP_CODE_SERVER_DIR")
MCP_CODE_SERVER_PORT = os.environ.get("MCP_CODE_SERVER_PORT")

REPO_ROOT_ABSOLUTE_PATH = "/home/martin/tfg_agentes_software"

CSV_DATASET_RELATIVE_PATH = "static/evaluation_dataset.csv"
CSV_DATASET_PRUEBA_RELATIVE_PATH = "static/evaluation_dataset_prueba.csv"

GRAPH_IMAGES_RELATIVE_PATH = "static/images"
OFFICIAL_DOCS_RELATIVE_PATH = "/sistema_agentes/static/gen_docs"
FULL_RAG_DOCS_DIR = "/home/martin/rag_tfg"
VISUAL_DOCS_RAG_DIR = f"{FULL_RAG_DOCS_DIR}/visual_docs"
GENERAL_DOCS_RAG_DIR = f"{FULL_RAG_DOCS_DIR}/gen_docs"
MOCK_DOCS_DOCS_RAG_DIR = f"{FULL_RAG_DOCS_DIR}/agente_google_drive_docs"

CODE_REPO_ROOT_ABSOLUTE_PATH = "/home/martin/open_source/ia-core-tools"

GITLAB_API_URL="https://gitlab.devops.lksnext.com/api/v4"
GITLAB_PROJECT_URL=1141
GITLAB_PROJECT_NORMAL_URL="https://gitlab.devops.lksnext.com/lks/genai/ia-core-tools"

GITLAB_MOCK_ISSUES="/home/martin/rag_tfg/gitlab/parsed_issues.json"
GITLAB_MOCK_COMMITS="/home/martin/rag_tfg/gitlab/commits.json"
GITLAB_MOCK_MEMBERS="/home/martin/rag_tfg/gitlab/members.json"

default_llm = ChatOpenAI(
    model="gpt-4.1-mini"
)
default_reasoner_llm = ChatOpenAI(
    model="o4-mini"
)


dummy_llm = ChatOpenAI(
    model="gpt-4.1-nano"
)

"""
default_llm = ChatOpenAI(
    model="gpt-4.1-nano"
)
default_reasoner_llm = ChatOpenAI(
    model="gpt-4.1-nano"
)
"""


"""
default_llm = ChatMistralAI(
    model="mistral-medium-latest"
)
default_reasoner_llm = ChatMistralAI(
    model="mistral-large-latest"
)
"""
"""
default_llm = ChatGroq(
    model="llama-3.1-8b-instant"
)
default_reasoner_llm = ChatGroq(
    model="llama-3.1-8b-instant"
)
"""

default_embedding_llm = OpenAIEmbeddings(
    model="text-embedding-3-small"
)
default_judge_llm = ChatOpenAI(
    model="gpt-4.1-mini"
)

db_user=os.getenv("DB_USER")
db_password=os.getenv("DB_PASSWORD")
db_host=os.getenv("DB_HOST")
db_port=os.getenv("DB_PORT")
db_name=os.getenv("DB_NAME")
postgre_connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
psycopg_connection_string = f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

PGVECTOR_COLLECTION_PREFIX="collection_"
STORE_COLLECTION_PREFIX="documents"

BACKEND_PORT = 5000