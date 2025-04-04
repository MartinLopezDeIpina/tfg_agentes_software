from src.db.models import FileChunk, FSEntry
from utils.utils import get_count_text_lines


class ChunkCreator:
    overlap_size: int

    # id chunk -> lista id chunks referenciados
    solved_references = dict()
    # id chunk -> lista nombres definiciones referenciadas
    not_solved_references = dict()
    # nombre definiciones -> lista chunks en las que se definen (puede que los chunks se solapen o que una referencia sea ambigua)
    name_definitions = dict()

    def __init__(self, db_session, chunk_max_line_size: int = 100, chunk_minimum_proportion: float = 0.2, overlap_size: int = 10):
        self.db_session = db_session
        self.chunk_max_line_size = chunk_max_line_size
        self.minimum_proportion = chunk_minimum_proportion
        # si mínimo queremos 20 líneas y máximo 100, entonces la esperada será 60
        self.chunk_expected_size =int((chunk_max_line_size + chunk_max_line_size * chunk_minimum_proportion) // 2)

    def solve_unsolved_references(self):
        for chunk_id, ref_names in self.not_solved_references.items():
            for ref_name in ref_names:
                if chunk_id not in self.solved_references:
                    self.solved_references[chunk_id] = set()
                self.solved_references[chunk_id].append(ref_name)

    def add_chunk_references_to_db(self):
        for chunk_id, ref_names in self.solved_references.items():
            chunk = self.db_session.query(FileChunk).filter(FileChunk.chunk_id==chunk_id).one()
            for ref_name in ref_names:
                chunk_id_definitions = self.name_definitions.get(ref_name)
                """
                En el caso de que un chunk sea referenciado por un chunk al que quiere referenciar no referenciarlo para evitar 
                dependencias cíclicas.
                En el caso de que la referencia sea una función que se define fuera del repositorio, chunk_id_definitions será None.
                """
                if chunk_id_definitions is not None:
                    chunk_id_definitions_copy = []
                    for chunk_id_definition in chunk_id_definitions:
                        if chunk_id_definition not in chunk.referencing_chunks:
                            chunk_id_definitions_copy.append(chunk_id_definition)
                    chunk_id_definitions = chunk_id_definitions_copy

                    definition_chunks = set()
                    for def_id in chunk_id_definitions:
                        definition_chunk = self.db_session.query(FileChunk).filter(FileChunk.chunk_id==def_id).one()
                        definition_chunks.add(definition_chunk)

                    for definition_chunk in definition_chunks:
                        # importante no añadirla si ya existe
                        if definition_chunk not in chunk.referenced_chunks and definition_chunk != chunk:
                            chunk.referenced_chunks.append(definition_chunk)

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
                defined_definitions.append(definition.name)
        for definition in defined_definitions:
            if definition not in self.name_definitions:
                self.name_definitions[definition] = []
            self.name_definitions[definition].append(chunk_id)

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

        chunk_size = chunk_end_line - chunk_start_line
        num_chunks = (chunk_size // self.chunk_max_line_size) + 1
        if num_chunks >= 2:
            chunk_size = (chunk_size // num_chunks) + 1
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
        """
        Crea los chunk y los añade a la base de datos.
        Aplica el overlap indicado.
        """
        chunk_start_line = min(0, chunk_start_line - self.overlap_size)
        chunk_end_line = max(0, chunk_end_line + self.overlap_size)

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
