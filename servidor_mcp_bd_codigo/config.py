import os
#from langchain_community.embeddings import OpenAIEmbeddings
from langchain_openai import OpenAIEmbeddings

from dotenv import load_dotenv
load_dotenv()

EMBEDDER_MODEL = "text-embedding-3-small"
EMBEDDER_MODEL_INSTANCE = OpenAIEmbeddings(
                model=EMBEDDER_MODEL
                )

MAX_LINE_LENGTH = 2000
MAX_CHUNKS = 10
MAX_REFERENCED_CHUNKS = 3
MAX_REFERENCING_CHUNKS = 3

LLM_TEMPERATURE = 0.5

TEST_EXAMPLE_FILES_PATH = "tests/chunker/example_files"

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

REPO_ROOT_ABSOLUTE_PATH = "/home/martin/open_source/ia-core-tools"

# directorios a ignorar solo para la visualización del aŕbol
TREE_STR_IGNORE_DIRS = [".git"]