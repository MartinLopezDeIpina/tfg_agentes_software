import contextlib
import json
import os
import io
import subprocess
import sys
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import List, Tuple
from treelib import Tree

from sqlalchemy.orm import Session
from langchain.prompts import PromptTemplate

from db.db_connection import DBConnection
from db.models import FileChunk, FSEntry

from src.utils.proyect_tree import generate_repo_tree_str
from src.utils.utils import execute_and_stream_command, get_file_text, get_start_to_end_lines_from_text_code, change_path_extension_to_md, get_file_absolute_path
from src.db.db_utils import get_chunk_code


@dataclass
class DocPromptPart:
    prompt_explanation: str
    prompt_part: str

class DocPromptBuilder:
    prompt_parts: List[DocPromptPart]
    prompt_template: PromptTemplate
    prompt_parts_explanation: dict

    def __init__(self):
        prompt_file_path = os.path.join(os.path.abspath(Path(__file__).parent), "doc_prompt/prompt.txt")
        prompt_text = get_file_text(prompt_file_path)
        self.prompt_template = PromptTemplate(
            input_variables=["chunk_code", "file_code", "file_path", "extra_docs", "repo_tree_str", "referenced_chunks", "referencing_chunks"],
            template=prompt_text
        )
        self.prompt_parts = []

        prompt_parts_explanation_file_path = os.path.join(os.path.abspath(Path(__file__).parent), "doc_prompt/prompt_parts.json")
        prompt_parts_explanation = get_file_text(prompt_parts_explanation_file_path)
        self.prompt_parts_explanation = json.loads(prompt_parts_explanation)

    def restart_prompt(self):
        self.prompt_parts = []

    def add_prompt_chunk_code(self, chunk_code: str):
        self.prompt_parts.append(DocPromptPart(self.prompt_parts_explanation["chunk_code"], chunk_code))

    def add_prompt_file_code(self, file_code: str, is_only_chunk_in_file: bool):
        """
        Si es el único chunk en el fichero, no hace falta añadir el código del fichero.
        """
        if not is_only_chunk_in_file:
            self.prompt_parts.append(DocPromptPart(self.prompt_parts_explanation["file_code"], file_code))

    def add_prompt_extra_docs(self, extra_docs: str):
        if extra_docs != "":
            self.prompt_parts.append(DocPromptPart(self.prompt_parts_explanation["extra_docs"], extra_docs))

    def add_prompt_repo_map(self, repo_map: str):
        self.prompt_parts.append(DocPromptPart(self.prompt_parts_explanation["repo_map"], repo_map))

    def add_prompt_referenced_chunks(self, referenced_chunks: List[Tuple[str, str]]):
        referenced_chunks_str = ""
        referenced_chunks_str += f"{self.prompt_parts_explanation["referenced_chunks"]}:\n"
        
        for chunk in referenced_chunks:
            referenced_chunks_str += f"{self.prompt_parts_explanation["referencing_chunk_path"]}: {chunk[0]}\n{chunk[1]}\n"
            
        self.prompt_parts.append(DocPromptPart(self.prompt_parts_explanation["referenced_chunks"], referenced_chunks_str))
        
    def add_prompt_referencing_chunks(self, referencing_chunks: List[Tuple[str, str]]):
        referencing_chunks_str = ""
        referencing_chunks_str += f"{self.prompt_parts_explanation["referencing_chunks"]}:\n"
        
        for chunk in referencing_chunks:
            referencing_chunks_str += f"{self.prompt_parts_explanation["referencing_chunk_path"]}: {chunk[0]}\n{chunk[1]}\n"
            
        self.prompt_parts.append(DocPromptPart(self.prompt_parts_explanation["referencing_chunks"], referencing_chunks_str))
        
    def build_prompt(self) -> str:
        """
        Construye el prompt a partir de las partes añadidas.
        """
        prompt = ""
        for part in self.prompt_parts:
            prompt += f"{part.prompt_explanation}:\n{part.prompt_part}\n\n"
        return prompt

class CodeDocGenerator:
    db_session: Session
    repo_path: str
    # líneas extra que se le pasan del fichero de cada chunk
    max_lines_per_file: int
    extra_docs: bool
    repo_tree_str: str
    doc_prompt_builder: DocPromptBuilder


    def __init__(self, repo_path: str, files_to_ignore: List[str] = None, max_lines_per_file: int = 200):
        if files_to_ignore is None:
            files_to_ignore = []

        self.repo_path = repo_path
        self.files_to_ignore = files_to_ignore
        self.max_lines_per_file = max_lines_per_file
        self.db_session = DBConnection.get_session()
        self.extra_docs = False
        self.doc_prompt_builder = DocPromptBuilder()

        self.repo_tree_str = generate_repo_tree_str(
            repo_path=self.repo_path,
            ignored_dirs=self.files_to_ignore
        )
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

    def create_chunk_documentation_prompt(self, chunk: FileChunk, file_path: str, file_code: str, file_extra_docs: str, is_only_chunk_in_file: bool):
        chunk_code = get_start_to_end_lines_from_text_code(file_code, chunk.start_line, chunk.end_line)
        referenced_chunks = chunk.referenced_chunks
        referencing_chunks = chunk.referencing_chunks

        referenced_chunks_tuples = []
        referencing_chunks_tuples = []
        for referenced_chunk in referenced_chunks:
            referenced_chunk_file_path = referenced_chunk.file.path
            chunk_code = get_chunk_code(self.db_session, referenced_chunk)
            referenced_chunks_tuples.append((referenced_chunk_file_path, chunk_code))
        for referencing_chunk in referencing_chunks:
            referencing_chunk_file_path = referencing_chunk.file.path
            chunk_code = get_chunk_code(self.db_session, referencing_chunk)
            referencing_chunks_tuples.append((referencing_chunk_file_path, chunk_code))

        self.doc_prompt_builder.restart_prompt()

        self.doc_prompt_builder.add_prompt_chunk_code(chunk_code)
        self.doc_prompt_builder.add_prompt_file_code(file_code, is_only_chunk_in_file)
        self.doc_prompt_builder.add_prompt_extra_docs(file_extra_docs)
        self.doc_prompt_builder.add_prompt_repo_map(self.repo_tree_str)
        self.doc_prompt_builder.add_prompt_referenced_chunks(referenced_chunks_tuples)
        self.doc_prompt_builder.add_prompt_referencing_chunks(referencing_chunks_tuples)

        chunk_doc_prompt = self.doc_prompt_builder.build_prompt()
        return chunk_doc_prompt

    def create_chunk_documentation(self, chunk: FileChunk, file_path: str, file_code: str, file_extra_docs: str, is_only_chunk_in_file: bool):
        chunk_doc_prompt = self.create_chunk_documentation_prompt(chunk, file_path, file_code, file_extra_docs)
        # todo -> llamar llm y asignarlo en db

    def get_file_extra_docs_if_exists(self, file_path: str) -> str:
        if self.extra_docs:
            extra_docs_file_path = os.path.join(self.extra_docs_path, file_path)
            extra_docs_file_path = change_path_extension_to_md(extra_docs_file_path)

            if os.path.exists(extra_docs_file_path):
                return get_file_text(extra_docs_file_path)
            else:
                return ""

    def create_file_chunks_documentation(self, file: FSEntry):
        is_only_chunk_in_file = len(file.chunks) == 1
        file_path = file.path
        file_absolute_path = os.path.join(self.repo_path, file_path)
        file_code = get_file_text(file_absolute_path)
        file_chunks = file.chunks
        file_extra_docs = self.get_file_extra_docs_if_exists(file_path)
        for chunk in file_chunks:
            self.create_chunk_documentation(chunk, file_path, file_code, file_extra_docs, is_only_chunk_in_file)

    def create_extra_docs_if_not_exists(self):
        extra_doc_exist = len(os.listdir(self.extra_docs_path)) > 0
        if not extra_doc_exist:
            self.generate_extra_docs()
        else:
            self.extra_docs = True

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
        
        self.create_extra_docs_if_not_exists()

        files_to_document = self.db_session.query(FSEntry).filter(FSEntry.is_directory == False).all()
        for file in files_to_document:
            self.create_file_chunks_documentation(file)
