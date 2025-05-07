from pathlib import Path
from typing import List

from rich.console import Console
from rich.markdown import Markdown


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

