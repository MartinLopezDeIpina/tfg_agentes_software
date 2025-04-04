import os
from typing import List

from src.utils.utils import execute_and_stream_command, change_path_extension_to_md, get_file_text

def generate_extra_docs(files_to_ignore: List[str], repo_path: str, extra_docs_path: str):
    """
    Genera documentación extra para los ficheros python del repositorio utilizando el agente RepoAgent.
    """
    try:
        files_to_ignore_str = ",".join(files_to_ignore)
        command = f"repoagent run --model gpt-4o-mini --target-repo-path {repo_path} --markdown-docs-path {extra_docs_path} --ignore-list {files_to_ignore_str}"
        exit_code = execute_and_stream_command(command)
        if exit_code != 0:
            print(f"Error al generar documentación extra {command}: Código de salida {exit_code}")
    except Exception as e:
        print(f"Error al generar documentación extra: {e}")
        extra_docs = False

def get_extra_docs_if_exists(file_relative_path: str, extra_docs_path: str) -> str:
    extra_docs_file_path = os.path.join(extra_docs_path, file_relative_path)
    extra_docs_file_path = change_path_extension_to_md(extra_docs_file_path)

    if os.path.exists(extra_docs_file_path):
        return get_file_text(extra_docs_file_path)
    else:
        return ""
