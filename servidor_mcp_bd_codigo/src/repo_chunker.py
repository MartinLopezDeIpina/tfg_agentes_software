import os

from grep_ast.tsl import get_language, get_parser  # noqa: E402
from grep_ast import filename_to_lang
from importlib import resources
from src.db.models import FSEntry, Ancestor, FileChunk
from src.db.db_utils import add_fs_entry
from src.db.db_connection import DBConnection

from src.utils import get_file_text

def analyze_file_abstract_syntaxis_tree(code_text: str, file_path: str):
    language = filename_to_lang(file_path)
    if not language:
        raise Exception(f"File {file_path} has no language")

    lang = get_language(language)
    parser = get_parser(language)

    scm_file = resources.files(__package__).joinpath(
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
    def __init__(self, chunk_max_line_size: int = 500, chunk_expected_size: int = 250):
        self.chunk_max_line_size = chunk_max_line_size
        self.chunk_expected_size = chunk_expected_size

    def chunk_file_simple(file_path: str):
        """
        Si el análisis del árbol falla, dividir por líneas.
        """
        pass
    
    def definition_is_inside_chunk(self, definition, chunk_start_line, chunk_end_line):
        """
        La propia definición de la clase debe estar dentro del chunk
        Se tienen en cuenta las definiciones que entren enteras en el chunk, parcialmente por arriba y parcialmente por abajo
        """
        inside_chunk = definition.start_point.row >= chunk_start_line and definition.end_point.row <= chunk_end_line
        partially_inside_chunk_above = definition.start_point.row <= chunk_start_line and definition.end_point.row >= chunk_start_line
        partially_inside_chunk_below = definition.start_point.row <= chunk_end_line and definition.end_point.row >= chunk_end_line

        return inside_chunk or partially_inside_chunk_above or partially_inside_chunk_below

    def anotate_definitions(self, chunk_id, definitions, chunk_start_line, chunk_end_line):
        """
        Si la definición a anotar es una clase, debería tener definiciones de funciones internas
        """
        defined_definitions = []
        for definition in definitions:
            definition_is_inside_chunk = self.definition_is_inside_chunk(definition, chunk_start_line, chunk_end_line)
            if (definition_is_inside_chunk):
                defined_definitions.append(definition)
        for definition in defined_definitions:
            if definition.text.decode("utf-8") not in self.name_definitions:
                self.name_definitions[definition.text.decode("utf-8")] = []
            self.name_definitions[definition.text.decode("utf-8")].append(chunk_id)

    def anotate_references(self, chunk_id, references, chunk_start_line, chunk_end_line):
        self.solved_references[chunk_id] = []
        self.not_solved_references[chunk_id] = []
        for reference in references:
            if reference.start_point.row >= chunk_start_line and reference.end_point.row <= chunk_end_line:
                reference_text = reference.text.decode("utf-8")
                if reference_text in self.name_definitions:
                    if chunk_id not in self.solved_references:
                        self.solved_references[chunk_id] = []
                    self.solved_references[reference_text].append(chunk_id)
                else:
                    if chunk_id not in self.not_solved_references:
                        self.not_solved_references[chunk_id] = []
                    self.not_solved_references[reference_text].append(chunk_id)

    def chunk_file(self, file_path: str, parent_id: int):
        file_entry = add_fs_entry(
            session=self.db_session,
            name=os.path.basename(file_path),
            parent_id=parent_id,
            is_directory=False
        )

        try:
            code_text = get_file_text(file_path)
        except Exception as e:
            print(f"error, could not read file {file_path}: {e}")

        try:
            if file_path == "/home/martin/open_source/ia-core-tools/app/tools/pgVectorTools.py":
                print("debug")
            abstract_tree_captures = analyze_file_abstract_syntaxis_tree(code_text, file_path)

            definitions = abstract_tree_captures["definition.class"] + abstract_tree_captures["definition.function"]
            definitions.sort(key=lambda d: d.start_point.row)

            references = abstract_tree_captures["name.reference.call"]
            references.sort(key=lambda d: d.start_point.row)

            chunk_start_line = 0
            chunk_end_line = 0
            definition_index = 0
            finished = False
            """
            Si una clase es más grande que el tamaño máximo del chunk, entonces dividirla en varios chunks
            A la hora de dividirla tener en cuenta las funciones internas de la misma forma
            """
            while not finished:
                current_definition = definitions[definition_index]

                # todo: gestionar el caso en el que la definición es muy corta, ¿añadir varias funciones en el mismo chunk? -> igual no, valorarlo
                if current_definition.end_point.row + chunk_start_line <= self.chunk_max_line_size:
                    chunk_end_line = current_definition.end_point.row
                    chunk_start_line = current_definition.start_point.row

                    #todo: los embeddings calcularlos y añadirlos al final, mirar para hacerlo en forma de batch
                    chunk = FileChunk(
                        session=self.db_session,
                        file_id=file_entry.id,
                        start_line=chunk_start_line,
                        end_line=chunk_end_line
                    )
                    self.db_session.add(chunk)
                    chunk_id = chunk.chunk_id

                    self.anotate_definitions(chunk_id, definitions, chunk_start_line, chunk_end_line)
                    self.anotate_references(chunk_id, references, chunk_start_line, chunk_end_line)

                else:
                    #todo
                    pass






        except Exception as e:
            print(f"error, could not analyze file {file_path}: {e}")
            self.chunk_file_simple(file_path)


    def chunk_directory_recursive(self, dir_path: str, parent_id: int):
        directory_entry = add_fs_entry(
            session=self.db_session,
            name=os.path.basename(dir_path),
            parent_id=parent_id,
            is_directory=True
        )

        for entry in os.listdir(dir_path):
            entry_path = os.path.join(dir_path, entry)

            if os.path.isdir(entry_path):
                self.chunk_directory_recursive(
                    dir_path=entry_path,
                    parent_id=directory_entry.id
                )
            elif os.path.isfile(entry_path):
                self.chunk_file(
                    file_path=entry_path,
                    parent_id=directory_entry.id
                )

    def chunk_repo(self, repo_path: str, chunk_max_line_size: int = 500, chunk_expected_size: int = 250):
        """
        Se divide el repositorio en chunks.
        Se analizan las definiciones y referencias de cada chunk, si el nombre de la referencia ha sido definida se añade
        al diccionario de referencias resueltas, si no se añade al diccionario de referencias no resueltas.
        """
        self.chunk_max_line_size = chunk_max_line_size
        self.chunk_expected_size = chunk_expected_size
        self.solved_references = dict()
        self.not_solved_references = dict()
        self.name_definitions = dict()
        self.db_session = DBConnection.get_instance()

        fs_entry = add_fs_entry(
            session=self.db_session,
            name=os.path.basename(repo_path),
            parent_id=None,
            is_directory=True
        )
        root_node_id = fs_entry.id

        self.chunk_directory_recursive(repo_path, root_node_id)

        #todo: resolver las referencias no resueltas
        #todo: añadir las referencias de los chunks desde el diccionario de referencias resueltas

        self.db_session.commit()
