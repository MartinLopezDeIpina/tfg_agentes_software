import os
#from langchain_community.embeddings import OpenAIEmbeddings
from langchain_openai import OpenAIEmbeddings

from dotenv import load_dotenv
load_dotenv()

EMBEDDER_MODEL = "text-embedding-3-small"

EMBEDDER_MODEL_INSTANCE = None
try:
    EMBEDDER_MODEL_INSTANCE = OpenAIEmbeddings(
                    model=EMBEDDER_MODEL
                    )
except Exception as e:
    print("No se ha establecido la api key de openai")

MAX_LINE_LENGTH = 2000
MAX_CHUNKS = 3
MAX_REFERENCED_CHUNKS = 1
MAX_REFERENCING_CHUNKS = 1

LLM_TEMPERATURE = 0.5

DIRECTROY_TO_INDEX=os.getenv("DIRECTORY_TO_INDEX")

# No se usa para los tests por lo que no es necesario cambiarlo
REPO_ROOT_ABSOLUTE_PATH = os.environ.get("REPO_ROOT_ABSOLUTE_PATH", "/home/martin/open_source/ia-core-tools")

TEST_EXAMPLE_FILES_PATH = "tests/chunker/example_files"
ROOT_DIR = os.environ.get("ROOT_DIR", os.path.dirname(os.path.abspath(__file__)))

# directorios a ignorar solo para la visualización del aŕbol
TREE_STR_IGNORE_DIRS = [".git"]

files_to_ignore = [".git",
                   "app/static/css/style.css",
                   "app/static/js/bootstrap.bundle.js",
                   "app/static/js/bootstrap.bundle.min.js",
                   "app/static/vendor"]

