import asyncio
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
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage

from db.db_connection import DBConnection
from db.models import FileChunk, FSEntry

from src.utils.proyect_tree import generate_repo_tree_str
from src.utils.utils import execute_and_stream_command, get_file_text, get_start_to_end_lines_from_text_code, change_path_extension_to_md, get_file_absolute_path, tab_all_lines
from src.db.db_utils import get_chunk_code

from src.code_indexer.prompts import user_prompt, system_prompt, prompt_parts_explanation

from src.code_indexer.doc_llm_prompter import AsyncLLMPrompter

@dataclass
class DocPromptPart:
    prompt_explanation: str
    prompt_part: str

class DocPromptBuilder:
    prompt_parts: List[DocPromptPart]
    system_prompt: str
    user_prompt_template: PromptTemplate
    prompt_parts_explanation: dict
    max_reference_chunks: int = 10
    max_file_extra_lines: int = 300

    def __init__(self, max_reference_chunks: int = 10, max_file_extra_lines: int = 300):
        self.max_reference_chunks = max_reference_chunks
        self.max_file_extra_lines = max_file_extra_lines

        self.system_prompt = system_prompt
        self.user_prompt_template = PromptTemplate(
            input_variables=["input_resources"],
            template=user_prompt
        )
        self.prompt_parts = []
        self.prompt_parts_explanation = prompt_parts_explanation

    def restart_prompt(self):
        self.prompt_parts = []

    def add_prompt_chunk_code(self, chunk_code: str, file_path: str):
        prompt_explanation = f"{self.prompt_parts_explanation["chunk_code"]} for file {file_path}"
        self.prompt_parts.append(DocPromptPart(prompt_explanation, chunk_code))

    def add_prompt_file_code(self, file_code: str, is_only_chunk_in_file: bool, chunk_start_line: int, chunk_end_line: int):
        """
        Si es el único chunk en el fichero, no hace falta añadir el código del fichero.
        """
        if not is_only_chunk_in_file:
            max_lines_top_bottom = self.max_file_extra_lines // 2
            start_line = max(0, chunk_start_line - max_lines_top_bottom)
            end_line = min(chunk_end_line + max_lines_top_bottom, len(file_code.splitlines()) - 1)
            cut_file_code = get_start_to_end_lines_from_text_code(file_code, start_line, end_line)

            self.prompt_parts.append(DocPromptPart(self.prompt_parts_explanation["file_code"], cut_file_code))

    def add_prompt_extra_docs(self, extra_docs: str):
        if extra_docs != "":
            self.prompt_parts.append(DocPromptPart(self.prompt_parts_explanation["extra_docs"], extra_docs))

    def add_prompt_repo_map(self, repo_map: str):
        self.prompt_parts.append(DocPromptPart(self.prompt_parts_explanation["repo_map"], repo_map))

    def add_prompt_referenced_chunks(self, referenced_chunks: List[Tuple[str, str]]):
        if len(referenced_chunks) > 0:
            referenced_chunks_str = ""

            for chunk in referenced_chunks:
                tabed_chunk = tab_all_lines(chunk[1])
                referenced_chunks_str += f"\n-Referenced chunk in file {chunk[0]}:\n{tabed_chunk}\n"

            self.prompt_parts.append(DocPromptPart(self.prompt_parts_explanation["referenced_chunks"], referenced_chunks_str))
        
    def add_prompt_referencing_chunks(self, referencing_chunks: List[Tuple[str, str]]):
        if len(referencing_chunks) > 0:
            referencing_chunks_str = ""

            for chunk in referencing_chunks:
                referencing_chunks_str += f"{self.prompt_parts_explanation["referencing_chunk_path"]}: {chunk[0]}\n{chunk[1]}\n"

            self.prompt_parts.append(DocPromptPart(self.prompt_parts_explanation["referencing_chunks"], referencing_chunks_str))
        
    def build_prompt(self) -> List[BaseMessage]:
        """
        Construye el prompt a partir de las partes añadidas.
        """
        prompt_resources = ""
        for i, part in enumerate(self.prompt_parts):
            tabed_prompt_part = tab_all_lines(part.prompt_part)
            prompt_resources += f"{i+1}. {part.prompt_explanation}:\n{tabed_prompt_part}\n\n"

        user_prompt = self.user_prompt_template.format(input_resources=prompt_resources)
        prompt = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_prompt)
        ]

        return prompt

class CodeDocGenerator:
    db_session: Session
    repo_path: str
    # líneas extra que se le pasan del fichero de cada chunk
    max_lines_per_file: int
    extra_docs: bool
    repo_tree_str: str
    doc_prompt_builder: DocPromptBuilder
    doc_llm_prompter: AsyncLLMPrompter

    num_files_to_document: int
    num_files_documented: int
    num_chunks_to_document: int
    num_chunks_documented: int

    def __init__(self, repo_path: str, files_to_ignore: List[str] = None, max_referenced_chunks: int = 10, max_file_extra_lines: int = 200):
        if files_to_ignore is None:
            files_to_ignore = []

        self.repo_path = repo_path
        self.files_to_ignore = files_to_ignore
        self.max_reference_chunks = max_referenced_chunks
        self.max_file_extra_lines = max_file_extra_lines
        self.db_session = DBConnection.get_session()
        self.extra_docs = False
        self.doc_prompt_builder = DocPromptBuilder()
        self.doc_llm_prompter = AsyncLLMPrompter()

        self.repo_tree_str = generate_repo_tree_str(
            repo_path=self.repo_path,
            ignored_dirs=self.files_to_ignore
        )
        self.extra_docs_path = resources.files("servidor_mcp_bd_codigo").joinpath(
            "src",
            "code_indexer",
            "extra_docs"
        )

        self.num_files_documented = 0
        self.num_chunks_documented = 0

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

    def create_chunk_documentation_prompt(self, chunk: FileChunk, file_path: str, file_code: str, file_extra_docs: str, is_only_chunk_in_file: bool) -> List[BaseMessage]:
        chunk_code = get_start_to_end_lines_from_text_code(file_code, chunk.start_line, chunk.end_line)
        referenced_chunks = chunk.referenced_chunks
        referencing_chunks = chunk.referencing_chunks

        referenced_chunks_tuples = []
        referencing_chunks_tuples = []
        for referenced_chunk in referenced_chunks:
            referenced_chunk_file_path = referenced_chunk.file.path
            chunk_code = get_chunk_code(self.db_session, referenced_chunk, self.repo_path)
            referenced_chunks_tuples.append((referenced_chunk_file_path, chunk_code))
        for referencing_chunk in referencing_chunks:
            referencing_chunk_file_path = referencing_chunk.file.path
            chunk_code = get_chunk_code(self.db_session, referencing_chunk, self.repo_path)
            referencing_chunks_tuples.append((referencing_chunk_file_path, chunk_code))

        self.doc_prompt_builder.restart_prompt()

        self.doc_prompt_builder.add_prompt_chunk_code(chunk_code, file_path)
        self.doc_prompt_builder.add_prompt_file_code(file_code, is_only_chunk_in_file, chunk.start_line, chunk.end_line)
        self.doc_prompt_builder.add_prompt_extra_docs(file_extra_docs)
        self.doc_prompt_builder.add_prompt_repo_map(self.repo_tree_str)
        self.doc_prompt_builder.add_prompt_referenced_chunks(referenced_chunks_tuples)
        self.doc_prompt_builder.add_prompt_referencing_chunks(referencing_chunks_tuples)

        chunk_doc_prompt = self.doc_prompt_builder.build_prompt()
        return chunk_doc_prompt

    async def create_chunk_documentation(self, chunk: FileChunk, file_path: str, file_code: str, file_extra_docs: str, is_only_chunk_in_file: bool):
        if file_path == "app/tools/modelTools.py":
            print("debug")
        chunk_doc_prompt = self.create_chunk_documentation_prompt(chunk, file_path, file_code, file_extra_docs, is_only_chunk_in_file)
        chunk_doc_response = await self.doc_llm_prompter.async_execute_prompt(chunk_doc_prompt)
        chunk_doc = chunk_doc_response.content
        chunk.docs = chunk_doc

        self.num_chunks_documented += 1
        return chunk_doc

    def get_file_extra_docs_if_exists(self, file_path: str) -> str:
        if self.extra_docs:
            extra_docs_file_path = os.path.join(self.extra_docs_path, file_path)
            extra_docs_file_path = change_path_extension_to_md(extra_docs_file_path)

            if os.path.exists(extra_docs_file_path):
                return get_file_text(extra_docs_file_path)
            else:
                return ""

    async def create_file_chunks_documentation(self, file: FSEntry):
        is_only_chunk_in_file = len(file.chunks) == 1
        file_path = file.path
        file_absolute_path = os.path.join(self.repo_path, file_path)

        """
        En caso de que el fichero esté vacío, o contenga una codificación no válida, no se le 
        añade documentación. 
        """
        try:
            file_code = get_file_text(file_absolute_path)
            if file_code == "":
                raise Exception("El fichero está vacío")
        except Exception as e:
            print(f"Error al leer el fichero {file_absolute_path}: {e}")
            return

        file_chunks = file.chunks
        file_extra_docs = self.get_file_extra_docs_if_exists(file_path)

        tasks = []
        for chunk in file_chunks:
            task = self.create_chunk_documentation(
                chunk, file_path, file_code, file_extra_docs, is_only_chunk_in_file
            )
            tasks.append(task)

        await asyncio.gather(*tasks)
        self.num_files_documented += 1
        print(f"{self.num_files_documented} / {self.num_files_to_document} files, {self.num_chunks_documented} / {self.num_chunks_to_document} chunks. -> Docs completas: {file_path}")

    def create_extra_docs_if_not_exists(self):
        extra_doc_exist = len(os.listdir(self.extra_docs_path)) > 0
        if not extra_doc_exist:
            self.generate_extra_docs()
        else:
            self.extra_docs = True

    async def create_repo_code_chunk_documentation(self):
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

        files_to_ignore = self.db_session.query(FSEntry).filter(FSEntry.path.in_(self.files_to_ignore)).all()
        files_to_ignore_ids = [file.id for file in files_to_ignore]

        #files_to_document = self.db_session.query(FSEntry).filter(FSEntry.is_directory == False and FSEntry not in files_to_ignore_ids).all()
        files_to_document = self.db_session.query(FSEntry).filter(FSEntry.is_directory == False and FSEntry not in files_to_ignore_ids).limit(10).all()

        num_files = len(files_to_document)
        num_chunks = 0
        for file in files_to_document:
            num_chunks += len(file.chunks)

        print(f"Generando documentación para {num_files} ficheros")
        print(f"Total de chunks a documentar: {num_chunks}")
        self.num_files_to_document = num_files
        self.num_chunks_to_document = num_chunks

        tasks = [self.create_file_chunks_documentation(file) for file in files_to_document]
        await asyncio.gather(*tasks)

        print(f"Documentación generada para todos los {len(files_to_document)} archivos")

    def create_repo_code_chunk_documentation_asynchronously(self):
        asyncio.run(self.create_repo_code_chunk_documentation())
        self.db_session.commit()
