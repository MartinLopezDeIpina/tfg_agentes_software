import os
from typing import List

from grep_ast.tsl import get_language, get_parser  # noqa: E402
from grep_ast import filename_to_lang
from importlib import resources
from src.db.models import FSEntry, Ancestor, FileChunk
from src.db.db_utils import add_fs_entry
from src.db.db_connection import DBConnection
from src.utils import get_count_text_lines

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

    # id chunk -> lista id chunks referenciados
    solved_references = dict()
    # id chunk -> lista nombres definiciones referenciadas
    not_solved_references = dict()
    # nombre definiciones -> lista chunks en las que se definen (puede que los chunks se solapen o que una referencia sea ambigua)
    name_definitions = dict()

    db_session: None

    def __init__(self, chunk_max_line_size: int = 500, chunk_expected_size: int = 250):
        self.chunk_max_line_size = chunk_max_line_size
        self.chunk_expected_size = chunk_expected_size

    def solve_unsolved_references(self):
        for chunk_id, ref_names in self.not_solved_references.items():
            for ref_name in ref_names:
                if ref_name not in self.solved_references:
                    self.solved_references[ref_name] = set()
                self.solved_references[ref_name].append(chunk_id)

    def add_chunk_references_to_db(self):
        for chunk_id, ref_names in self.solved_references.items():
            chunk = self.db_session.query(FileChunk).filter(FileChunk.chunk_id==chunk_id).one()
            for ref_name in ref_names:
                chunk_id_definitions = self.name_definitions.get(ref_name)
                """
                En el caso de que un chunk sea referenciado por un chunk al que quiere referenciar no referenciarlo para evitar 
                dependencias cíclicas.
                """
                for chunk_id_definition in chunk_id_definitions:
                    if chunk.referencing_chunks.contains(chunk_id_definition):
                        chunk_id_definitions.remove(chunk_id_definition)
                chunk.referenced_chunks.extend(chunk_id_definitions)

    def chunk_file_simple(self, file_entry: FSEntry, code_text: str):
        """
        Si el análisis del árbol falla, dividir por líneas.
        """
        chunk_start_line = 0
        chunk_end_line = get_count_text_lines(code_text) - 1
        
        self.create_multiple_chunks(
            chunk_start_line=chunk_start_line,
            chunk_end_line=chunk_end_line,
            file_id=file_entry.id
        )

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
                    self.solved_references[chunk_id].append(reference_text)
                else:
                    if chunk_id not in self.not_solved_references:
                        self.not_solved_references[chunk_id] = []
                    self.not_solved_references[chunk_id].append(reference_text)

    def create_multiple_chunks(self, chunk_start_line: int, chunk_end_line: int, file_id: int, definitions: dict = None, references: dict = None):
        if definitions is None:
            definitions = {}
        if references is None:
            references = {}

        num_chunks = ((chunk_end_line - chunk_start_line) // self.chunk_expected_size) + 1
        chunk_size = (self.chunk_expected_size // num_chunks) + 1
        for i in range(num_chunks):
            self.create_chunk(
                chunk_start_line=chunk_start_line,
                chunk_end_line=chunk_start_line + chunk_size,
                definitions=definitions,
                references=references,
                file_id=file_id
            )
            chunk_start_line += chunk_size

    def create_chunk(self, chunk_start_line: int, chunk_end_line: int, definitions: dict, references: dict, file_id: int):
        chunk = FileChunk(
            file_id=file_id,
            start_line=chunk_start_line,
            end_line=chunk_end_line
        )
        self.db_session.add(chunk)
        self.db_session.flush()
        chunk_id = chunk.chunk_id

        self.anotate_definitions(chunk_id, definitions, chunk_start_line, chunk_end_line)
        self.anotate_references(chunk_id, references, chunk_start_line, chunk_end_line)
        return chunk.chunk_id

    def chunk_file(self, file_path: str, parent_id: int):
        file_entry = add_fs_entry(
            session=self.db_session,
            name=os.path.basename(file_path),
            parent_id=parent_id,
            is_directory=False
        )

        code_text = get_file_text(file_path)

        try:
            if file_path == "/home/martin/open_source/ia-core-tools/app/model/user.py":
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
            definitions.sort(key=lambda d: d.start_point.row)

            chunk_start_line = 0
            chunk_end_line = 0
            finished = False

            while not finished:
                definition_index = -1
                for i, definition in enumerate(definitions):
                    if definition.end_point.row > chunk_start_line:
                        current_definition = definition
                        definition_index = i
                        if i == (len(definitions) - 1):
                            # -1??
                            current_definition_end_line = get_count_text_lines(code_text)
                            finished = True
                        else:
                            current_definition_end_line = current_definition.end_point.row
                        break
                if definition_index == -1:
                    finished = True
                    break

                """
                Si la siguiente definición se puede meter en el chunk, crear el chunk directamente
                """
                if current_definition_end_line - chunk_start_line <= self.chunk_max_line_size:
                    self.create_chunk(
                        chunk_start_line=chunk_start_line,
                        chunk_end_line=current_definition_end_line,
                        definitions=definitions,
                        references=references,
                        file_id=file_entry.id
                    )
                else:
                    """
                    Si no se puede meter la siguiente definición, partir las líneas hasta ahora y la definición en varios chunks
                    En caso de que la definición sea una función, partirla en partes iguales
                    """
                    if str(current_definition.type) == "function_definition":
                        self.create_multiple_chunks(
                            chunk_start_line=chunk_start_line,
                            chunk_end_line=current_definition_end_line,
                            definitions=definitions,
                            references=references,
                            file_id=file_entry.id
                        )
                        """
                        En caso de que sea una clase, considerar las funciones internas
                        """
                    else:
                        """
                        Iterar sobre las sub definiciones de la clase e ir añadiendolas al chunk actual
                        Si el chunk sobrepasa el límite, pasar la subdefinición al siguiente chunk
                        Si la subdefinición es demasiado grande individualmente, partirla en varios chunks
                        """
                        chunk_end_line = current_definition_end_line
                        # no considerar la clase (current_definition), considerar todas las definiciones internas (funciones)
                        current_definitions = [defi for defi in definitions if defi.start_point.row >= chunk_start_line and defi.end_point.row >= chunk_end_line and defi.id != current_definition.id]
                        sub_chunk_start_line = chunk_start_line
                        last_added_chunk_index = -1
                        for i, current_definition_iteration in enumerate(current_definitions):
                            sub_chunk_end_line = current_definition_iteration.end_point.row
                            if sub_chunk_end_line - sub_chunk_start_line >= self.chunk_max_line_size:
                                if i - last_added_chunk_index > 0:
                                   self.create_chunk(
                                       chunk_start_line=sub_chunk_start_line,
                                       chunk_end_line=current_definitions[i-1].end_point.row,
                                       definitions=definitions,
                                       references=references,
                                       file_id=file_entry.id
                                   )
                                else:
                                    self.create_multiple_chunks(
                                        chunk_start_line=sub_chunk_start_line,
                                        chunk_end_line=current_definitions[i].end_point.row,
                                        definitions=definitions,
                                        references=references,
                                        file_id=file_entry.id
                                    )
                            # Si se llega al final de los subchunks sin problemas de espacio añadirlos directamente
                            elif i == (len(current_definitions)-1):
                                self.create_chunk(
                                    chunk_start_line=sub_chunk_start_line,
                                    chunk_end_line=current_definitions[i].end_point.row,
                                    definitions=definitions,
                                    references=references,
                                    file_id=file_entry.id
                                )

                chunk_start_line = current_definition_end_line

        except Exception as e:
            print(f"{file_path}: {e}")
            self.chunk_file_simple(file_entry, code_text)

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


    # todo: añadir directorios / ficheros a ignorar
    def chunk_repo(self, repo_path: str, ignored_entries: List[str] = None, chunk_max_line_size: int = 500, chunk_expected_size: int = 250):
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

        self.chunk_max_line_size = chunk_max_line_size
        self.chunk_expected_size = chunk_expected_size
        self.solved_references = dict()
        self.not_solved_references = dict()
        self.name_definitions = dict()
        self.db_session = DBConnection.get_session()
        self.ignored_entries = ignored_entries

        # crear chunks y referencias parciales
        self.chunk_directory_recursive(repo_path, None)

        # resolver referencias no resueltas
        self.solve_unsolved_references()

        # añadir referencias a base de datos
        self.add_chunk_references_to_db()

        self.db_session.commit()
