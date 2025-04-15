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