import os
from chunk import Chunk
from typing import List

from grep_ast.tsl import get_language, get_parser  # noqa: E402
from grep_ast import filename_to_lang
from importlib import resources
from tree_sitter import Point

from src.chunker.chunk_creator import ChunkCreator
from src.chunker.file_chunk_state import ChunkingContext, FinalState, StartState
from src.db.models import FSEntry, FileChunk
from src.db.db_connection import DBConnection

from src.utils import get_file_text, get_count_text_lines
from src.db.db_utils import get_fsentry_relative_path, add_fs_entry


def analyze_file_abstract_syntaxis_tree(code_text: str, file_path: str):
    language = filename_to_lang(file_path)
    if not language:
        raise Exception(f"File {file_path} has no language")

    lang = get_language(language)
    parser = get_parser(language)

    scm_file = resources.files("servidor_mcp_bd_codigo").joinpath(
        "src",
        "language_queries",
        f"{language}-tags.scm"
    )
    if not scm_file.exists():
        raise Exception(f"error, could not find {language}-tags.scm in package resources")

    query_scm = scm_file.read_text()

    tree = parser.parse(bytes(code_text, "utf-8"))

    query = lang.query(query_scm)
    captures = query.captures(tree.root_node)
    if not captures:
        raise Exception(f"error, could not find captures in file {file_path}")

    return captures

class FileChunker:
    chunk_creator: ChunkCreator

    def __init__(self, chunk_max_line_size: int = 100, chunk_minimum_proportion: float = 0.2):
        self.chunk_max_line_size = chunk_max_line_size
        self.chunk_minimum_proportion = chunk_minimum_proportion
        self.db_session = DBConnection().get_session()
        self.chunk_creator = ChunkCreator(
            db_session=self.db_session,
            chunk_minimum_proportion=self.chunk_minimum_proportion,
            chunk_max_line_size=self.chunk_max_line_size
        )

    def chunk_file(self, file_path: str, parent_id: int):
        file_entry = add_fs_entry(
            session=self.db_session,
            name=os.path.basename(file_path),
            parent_id=parent_id,
            is_directory=False
        )

        code_text = get_file_text(file_path)

        try:
            #if file_path == "/home/martin/open_source/ia-core-tools/app/tools/modelTools.py":
            #if file_path == "/home/martin/open_source/ia-core-tools/app/api/api.py":
            if file_path == "/home/martin/tfg_agentes_software/servidor_mcp_bd_codigo/tests/chunker/example_files/example_java.java":
                print("debug")
            abstract_tree_captures = analyze_file_abstract_syntaxis_tree(code_text, file_path)

            definitions = []
            if "definition.class" in abstract_tree_captures:
                definitions += abstract_tree_captures["definition.class"]
            if "definition.function" in abstract_tree_captures:
                definitions += abstract_tree_captures["definition.function"]
            definitions.sort(key=lambda d: d.start_point.row)

            references = []
            if "name.reference.call" in abstract_tree_captures:
                references += abstract_tree_captures["name.reference.call"]
            references.sort(key=lambda d: d.start_point.row)

            context = ChunkingContext(
                chunk_creator=self.chunk_creator,
                definitions=definitions,
                references=references,
                file_id=file_entry.id,
                file_line_size=get_count_text_lines(code_text)
            )
            state = StartState()
            while not isinstance(state, FinalState):
                state = state.handle(context)

        except Exception as e:
            print(f"{file_path}: {e}")
            self.chunk_creator.chunk_file_simple(file_entry, code_text)

    def chunk_directory_recursive(self, dir_path: str, parent_id: int):
        if dir_path in self.ignored_entries:
            return

        directory_entry = add_fs_entry(
            session=self.db_session,
            name=os.path.basename(dir_path),
            parent_id=parent_id,
            is_directory=True
        )

        for entry in os.listdir(dir_path):
            entry_path = os.path.join(dir_path, entry)

            try:
                if os.path.isdir(entry_path):
                    self.chunk_directory_recursive(
                        dir_path=entry_path,
                        parent_id=directory_entry.id
                    )
                elif os.path.isfile(entry_path):
                    if entry_path in self.ignored_entries:
                        return
                    self.chunk_file(
                        file_path=entry_path,
                        parent_id=directory_entry.id
                    )
            except Exception as e:
                print(f"error, could not analyze file {entry_path}: {e}")

    def chunk_repo(self, repo_path: str, ignored_entries: List[str] = None):
        """
        Se divide el repositorio en chunks.
        Se analizan las definiciones y referencias de cada chunk, si el nombre de la referencia ha sido definida se añade
        al diccionario de referencias resueltas, si no se añade al diccionario de referencias no resueltas.
        Finalmente se añaden las referencias a la base de datos
        """
        if ignored_entries is None:
            ignored_entries = []
        for i, ignored_entry in enumerate(ignored_entries):
            ignored_entry_path = os.path.join(repo_path, ignored_entry)
            ignored_entries[i] = ignored_entry_path

        self.solved_references = dict()
        self.not_solved_references = dict()
        self.name_definitions = dict()
        self.db_session = DBConnection.get_session()
        self.ignored_entries = ignored_entries

        # crear chunks y referencias parciales
        self.chunk_directory_recursive(repo_path, None)

        # resolver referencias no resueltas
        self.chunk_creator.solve_unsolved_references()

        # añadir referencias a base de datos
        self.chunk_creator.add_chunk_references_to_db()

        self.db_session.flush()
        self.db_session.commit()

        print(f"\n\n\n#####\n\nTodo el repo chunkeado: {repo_path}\n\n#####")

    def visualize_chunks(self, repo_path: str):
        session = DBConnection.get_session()
        repo_files = session.query(FSEntry).filter(FSEntry.is_directory==False).all()
        for file in repo_files:
            if file.name.endswith(".py"):
                print(f"\n\n\nfile: {file.name}\n\n")
                for chunk in file.chunks:
                    referenced_chunks_ids = [chunk.chunk_id for chunk in chunk.referenced_chunks]
                    print(f"chunk: {chunk.chunk_id}, start_line: {chunk.start_line}, end_line: {chunk.end_line}")
                    print(f"referenced_chunks: {referenced_chunks_ids}")
                    file_relative_path = get_fsentry_relative_path(file)
                    file_absolute_path = os.path.join(repo_path, file_relative_path)
                    code_text = get_file_text(file_absolute_path)
                    code_lines = code_text.splitlines()
                    for i in range(chunk.start_line, chunk.end_line):
                        try:
                            print(code_lines[i])
                        except Exception as e:
                            pass
                    print("\n\n")

    def visualize_chunks_with_references(self, repo_path):
        session = DBConnection.get_session()
        repo_files = session.query(FSEntry).filter(FSEntry.is_directory==False).all()
        for file in repo_files:
            if file.name.endswith(".py"):
                print(f"\n\n\nfile: {file.name}\n\n")
                for chunk in file.chunks:
                    referenced_chunks_ids = [chunk.chunk_id for chunk in chunk.referenced_chunks]
                    print(f"chunk: {chunk.chunk_id}, start_line: {chunk.start_line}, end_line: {chunk.end_line}")
                    print(f"referenced_chunks: {referenced_chunks_ids}")
                    file_relative_path = get_fsentry_relative_path(file)
                    file_absolute_path = os.path.join(repo_path, file_relative_path)
                    code_text = get_file_text(file_absolute_path)
                    code_lines = code_text.splitlines()
                    for i in range(chunk.start_line, chunk.end_line):
                        try:
                            print(code_lines[i])
                        except Exception as e:
                            pass
                    print("\n\n")
                    print("Referenced chunks: \n##########")
                    for i in range(len(referenced_chunks_ids)):
                        referenced_chunk = session.query(FileChunk).filter(FileChunk.chunk_id == referenced_chunks_ids[i]).one()
                        referenced_chunk_file_id = referenced_chunk.file_id
                        referenced_chunk_file = session.query(FSEntry).filter(referenced_chunk_file_id == FSEntry.id).one()
                        referenced_chunk_file_relative_path = get_fsentry_relative_path(referenced_chunk_file)
                        referenced_chunk_file_absolute_path = os.path.join(repo_path, referenced_chunk_file_relative_path)
                        referenced_chunk_code_text = get_file_text(referenced_chunk_file_absolute_path)
                        referenced_chunk_code_lines = referenced_chunk_code_text.splitlines()
                        referenced_chunk_text = referenced_chunk_code_lines[referenced_chunk.start_line:referenced_chunk.end_line]
                        print(f"chunk {referenced_chunk.chunk_id}:")
                        for line in referenced_chunk_text:
                            print(line)
                        print()
                    print("###########")
