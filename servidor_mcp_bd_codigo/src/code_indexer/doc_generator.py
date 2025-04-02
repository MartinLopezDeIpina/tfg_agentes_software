import contextlib
import os
import io
import subprocess
import sys
from importlib import resources
from typing import List
from treelib import Tree

from sqlalchemy.orm import Session

from db.db_connection import DBConnection
from db.models import FileChunk

from src.utils.proyect_tree import generate_repo_tree_str
from src.utils.utils import execute_and_stream_command, get_file_text

class CodeDocGenerator:
    db_session: Session
    repo_path: str
    # líneas extra que se le pasan del fichero de cada chunk
    max_lines_per_file: int
    extra_docs: bool
    repo_tree_str: str


    def __init__(self, repo_path: str, files_to_ignore: List[str] = None, max_lines_per_file: int = 200):
        if files_to_ignore is None:
            files_to_ignore = []

        self.repo_path = repo_path
        self.files_to_ignore = files_to_ignore
        self.max_lines_per_file = max_lines_per_file
        self.db_session = DBConnection.get_session()
        self.extra_docs = False


        self.extra_docs_path = resources.files("servidor_mcp_bd_codigo").joinpath(
            "src",
            "code_indexer",
            "extra_docs"
        )

    def generate_extra_docs(self):
        """
        Genera documentación extra para los ficheros python del repositorio utilizando el agente RepoAgent.
        """
        try:
            files_to_ignore_str = ",".join(self.files_to_ignore)
            command = f"repoagent run --model gpt-4o-mini --target-repo-path {self.repo_path} --markdown-docs-path {self.extra_docs_path} --ignore-list {files_to_ignore_str}"
            exit_code = execute_and_stream_command(command)
            if exit_code == 0:
                self.extra_docs = True
            else:
                print(f"Error al generar documentación extra {command}: Código de salida {exit_code}")
        except Exception as e:
            print(f"Error al generar documentación extra: {e}")
            self.extra_docs = False

    def create_repo_code_chunk_documentation(self):
        """
        Genera documentación de los chunks presentes en la base de datos.
        La documentación se almacena en la columna docs de la tabla FileChunk.
        Se le indica a un LLM los siguientes datos de cada chunk:
        - El código del chunk a documentar
        - El código del fichero del que proviene el chunk, recortado de ser demasiado largo
        - Un árbol con los nombres de los ficheros del repositorio
        - Chunks a los que el chunk hace referencia, junto a su path en el proyecto
        - Documentación del fichero generada por el agente RepoAgent en caso de existir
        """

        existe_documentacion_extra = len(os.listdir(self.extra_docs_path)) > 0
        if not existe_documentacion_extra:
            self.generate_extra_docs()
        else:
            self.extra_docs = True
        self.repo_tree_str = generate_repo_tree_str(
            repo_path=self.repo_path,
            ignored_dirs=self.files_to_ignore
        )

        files_to_document = self.db_session.query(FileChunk).all()
        for file in files_to_document:
            #file_code = get_file_text(file.file_path)
            pass



