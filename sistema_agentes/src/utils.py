from pathlib import Path
from typing import List

from langchain_core.messages import AIMessage
from langgraph.store.base import Item, SearchItem
from rich.console import Console
from rich.markdown import Markdown

from src.specialized_agents.citations_tool.models import Citation


def tab_all_lines_x_times(text: str, times: int = 1) -> str:
    """
    Añade x tabulaciones a cada línea de un texto.
    """
    lines = text.splitlines()
    tabbed_lines = ["\t" * times + line for line in lines]
    return "\n".join(tabbed_lines)

def print_markdown(string: str):
    console = Console()
    md = Markdown(string)
    console.print(md)

def get_list_from_string_comma_separated_values(values_string: str):
    values_list = [element.strip() for element in values_string.split(',')]
    return values_list

def get_list_string_with_indexes(list: List[str]) -> str:
    string_result = ""
    for i, element in enumerate(list):
        string_result += f"{i}. {element}\n\n"

    return string_result

def read_file_content(file: Path) -> str:
    try:
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
        return content

    except Exception as e:
        print(f"Error leyendo fichero {file}")
        return ""
    
def get_memory_prompt_from_docs(memory_docs: List[SearchItem]) -> List[AIMessage]:
    """
    Devuelve la descripción de varios documentos extraídos de una colección de memoria
    """
    memories_list = []
    for i, memory in enumerate(memory_docs):
        cites = [Citation.from_string(citation) for citation in memory.value.get("cites")]
        cites_string = f"-Cited documents: {",".join([cite.doc_name for cite in cites])}"
        memory_string = f"Memory passage {i}: {memory.value.get("concept")}\n\t{cites_string}"
        memories_list.append(
            AIMessage(
                content=memory_string
            )
        )
    return memories_list



