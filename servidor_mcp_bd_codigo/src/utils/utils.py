import os
import subprocess
import sys
from pathlib import Path
import re
from config import MAX_LINE_LENGTH
from config import ROOT_DIR

def get_file_text(path: str) -> str:
    """
    Reads the content of a file and returns it as a string.

    Args:
        path (str): The path to the file.

    Returns:
        str: The content of the file.
    """
    result = []
    with open(path, 'r', encoding='utf-8') as file:
        for line in file:
            result.append(line[:MAX_LINE_LENGTH])
    return ''.join(result)

def get_count_text_lines(text: str) -> int:
    """
    Devuelve el número de líneas en un chunk de texto.
    """
    return len(text.splitlines()) + 1

def get_start_to_end_lines_from_text_code(file_text: str, start_line: int, end_line: int) -> str:
    """
    Devuelve las líneas de un fichero entre la línea inicial y la final.
    """
    texto_lineas = file_text.splitlines()
    lineas = texto_lineas[start_line : end_line + 1]
    return "\n".join(lineas)

def get_file_absolute_path(relativa_path: str):
    """
    Devuelve la ruta absoluta teniendo en cuenta el módulo superior del proyecto.
    """
    root_dir = Path(__file__).resolve().parent.parent.parent
    return os.path.join(root_dir, relativa_path)

def get_file_absolute_path_from_proyect_relative_path(relative_path: str, proyect_path: str = ROOT_DIR):
    """
    Devuelve la ruta absoluta en el sistema de ficheros desde la ruta relativa respecto al
    módulo de python.
    """
    file_path = os.path.join(proyect_path, relative_path)

    return file_path

def get_file_absolute_path_from_path(path: Path):
    return os.path.abspath(path)

def execute_and_stream_command(command: str):
    proceso = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # Redirige stderr a stdout
        text=True,
        bufsize=1
    )

    # Lee y muestra la salida línea por línea mientras el comando se ejecuta
    for line in proceso.stdout:
        print(line, end='')
        sys.stdout.flush()

    exit_code = proceso.wait()
    return exit_code

def change_path_extension_to_md(file_path: str) -> str:
    new_path = re.sub(r'\.([^\.]+)$', '.md', file_path)
    return new_path

def tab_all_lines(text: str) -> str:
    """
    Añade tabulación a todas las líneas de un texto.
    """
    return tab_all_lines_x_times(text, 1)

def tab_all_lines_x_times(text: str, times: int = 1) -> str:
    """
    Añade x tabulaciones a cada línea de un texto.
    """
    lines = text.splitlines()
    tabbed_lines = ["\t" * times + line for line in lines]
    return "\n".join(tabbed_lines)

def apend_with_x_tab_to_text(text: str, text_to_add: str, times_to_tab: int = 1):
    tabbed_text = tab_all_lines_x_times(text_to_add, times_to_tab)
    return text + tabbed_text
