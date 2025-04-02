import os
import subprocess
import sys
from pathlib import Path


def get_file_text(path: str) -> str:
    """
    Reads the content of a file and returns it as a string.

    Args:
        path (str): The path to the file.

    Returns:
        str: The content of the file.
    """
    with open(path, 'r', encoding='utf-8') as file:
        return file.read()

def get_count_text_lines(text: str) -> int:
    """
    Devuelve el número de líneas en un chunk de texto.
    """
    return len(text.splitlines()) + 1

def obtain_file_absolute_path(relativa_path: str):
    """
    Devuelve la ruta absoluta teniendo en cuenta el módulo superior del proyecto.
    """
    root_dir = Path(__file__).resolve().parent.parent.parent
    return os.path.join(root_dir, relativa_path)

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

