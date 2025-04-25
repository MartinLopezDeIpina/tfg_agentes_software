from abc import ABC, abstractmethod
from typing import List, Any

from src.chunker.chunk_creator import ChunkCreator
from src.chunker.chunk_objects import Definition

class ChunkingContext:
    chunk_creator: ChunkCreator
    definitions: List[Definition]
    references: List[Any]
    file_id: int
    def __init__(self, chunk_creator: ChunkCreator, definitions: List[Definition], references: List[Any], file_id: int, file_line_size: int):
        self.chunk_creator = chunk_creator
        self.definitions = definitions
        self.references = references
        self.file_id = file_id
        self.chunk_max_line_size = chunk_creator.chunk_max_line_size
        self.file_line_size = file_line_size
        self.create_last_chunk = False

        # Variables de estado
        self.chunk_start_line = 0
        self.chunk_end_line = 0
        self.current_chunk_definitions = []
        # Índice de definición a evaluar, sin estar en el chunk
        self.next_definition_index = 0

        # Variables para el procesamiento de clases
        self.class_definitions = []
        self.class_next_definition_index = 0

    def current_definition_is_last(self):
        return self.next_definition_index >= len(self.definitions)

    def next_definition_is_last(self):
        return self.next_definition_index + 1 >= len(self.definitions)

    def get_current_chunk_size(self):
        return self.chunk_end_line - self.chunk_start_line

    def last_definition_too_small(self):
        return self.file_line_size - self.chunk_end_line < self.chunk_max_line_size * self.chunk_creator.minimum_proportion

    def next_definition_is_last_and_too_small(self):
        return self.next_definition_is_last() and self.last_definition_too_small()

    def current_class_definition_is_last(self):
        return self.class_next_definition_index >= len(self.class_definitions)

    def next_definition_should_be_added_to_current_chunk(self):
        """
        Si la definición cabe en el chunk actual añadirla y repetir
        En caso de que la siguiente definición no quepa, pero que el chunk actual sea muy pequeño, añadirlo
        En caso de que la siguiente definición no quepa, pero si es la última definición y el chunk quedaría muy pequeño, añadirlo
        """
        next_definition = self.definitions[self.next_definition_index]
        # Considerar las líneas entre el final del chunk actual y el inicio de la siguiente definición como parte de la siguiente definición
        next_definition_line_size = next_definition.end_point.row - self.chunk_end_line
        current_chunk_size = self.chunk_end_line - self.chunk_start_line

        next_definition_fits_current_chunk = next_definition_line_size + current_chunk_size <= self.chunk_max_line_size
        current_chunk_too_small = current_chunk_size <= self.chunk_max_line_size * self.chunk_creator.minimum_proportion

        return next_definition_fits_current_chunk or current_chunk_too_small or self.next_definition_is_last_and_too_small()

    def current_definition_is_class(self):
        return self.definitions[self.next_definition_index - 1].is_class
    def next_definition_is_class(self):
        return self.definitions[self.next_definition_index].is_class

    def add_next_definition_to_current_chunk(self):
        next_definition = self.definitions[self.next_definition_index]
        self.current_chunk_definitions.append(next_definition)
        self.chunk_end_line = next_definition.end_point.row
        self.next_definition_index += 1

    def add_remaining_lines_to_chunk_if_last_definition(self):
        """
        Si las últimas líneas sin definición son suficientes como para crear un chunk, crearlo
        """
        if self.current_definition_is_last():
            remaining_lines = self.file_line_size - self.chunk_end_line
            if remaining_lines >= self.chunk_max_line_size * self.chunk_creator.minimum_proportion:
                self.create_last_chunk=True
            else:
                self.chunk_end_line = self.file_line_size
    
    def create_chunk(self):
        if self.chunk_end_line - self.chunk_start_line > self.chunk_max_line_size:
            self.chunk_creator.create_multiple_chunks(
                chunk_start_line=self.chunk_start_line,
                chunk_end_line=self.chunk_end_line,
                definitions=self.definitions,
                references=self.references,
                file_id=self.file_id
            )
        else:
            self.chunk_creator.create_chunk(
                chunk_start_line=self.chunk_start_line,
                chunk_end_line=self.chunk_end_line,
                definitions=self.definitions,
                references=self.references,
                file_id=self.file_id
            )
        self.current_chunk_definitions = []
        self.chunk_start_line = self.chunk_end_line


class ChunkingState(ABC):
    @abstractmethod
    def handle(self, context: ChunkingContext):
        """
        Procesa el estado actual y retorna el siguiente estado
        """
        pass

class StartState(ChunkingState):
    def handle(self, context: ChunkingContext):
        """
        Iniciar el primer chunk con las líneas hasta la primera definición
        """
        if len(context.definitions) == 0:
            # Si no hay definiciones usar un simple chunk lanzando excepción
            raise ValueError("No definitions found in the file.")

        first_definition_start = context.definitions[0].start_point.row
        context.chunk_end_line = first_definition_start - 1

        return EmptyChunkState()

class EmptyChunkState(ChunkingState):
    def handle(self, context: ChunkingContext):

        if context.current_definition_is_last():
            return AddLastLinesState()

        if context.next_definition_should_be_added_to_current_chunk():
            context.add_next_definition_to_current_chunk()
            
            # Si es la última definición, crear el chunk
            if context.current_definition_is_last():
                return CreateChunkState()

            return EmptyChunkState()
        else:
            return FullChunkState()

class FullChunkState(ChunkingState):
    """
    Si el chunk contiene al menos una definición, entonces crear el chunk, si no, la siguiente definición será demasiado
    grande como para caben en un único chunk.
    """
    def handle(self, context):
        if len(context.current_chunk_definitions) > 0:
            return CreateChunkState()
        else:
            return BigChunkState()
    
class BigChunkState(ChunkingState):
    def handle(self, context):
        """
        Si la definición es una función, dividirla en múltiples chunks
        Si es una clase, procesarla internamente con sus funciones
        """
        if context.next_definition_is_class():
            return StartClassState()
        else:
            context.add_next_definition_to_current_chunk()
            return CreateChunkState()

class CreateChunkState(ChunkingState):
    """
    Crea un chunk con las definiciones acumuladas en el contexto.
    Si el chunk supera el tamaño máximo, se divide en múltiples chunks.
    """
    def handle(self, context):
        context.add_remaining_lines_to_chunk_if_last_definition()
        context.create_chunk()

        return EmptyChunkState()
        
class StartClassState(ChunkingState):
    """
    La definición de la clase es la siguiente definición
    """    
    def handle(self, context):
        class_definition = context.definitions[context.next_definition_index]
        context.class_definitions = [
            defi for defi in context.definitions
            if defi.start_point.row >= class_definition.start_point.row
            and defi.end_point.row <= class_definition.end_point.row
            and defi != class_definition
        ]

        # En caso de que no se detecte ninguna función en la clase chunkear la función directamente
        if len(context.class_definitions) == 0:
            context.add_next_definition_to_current_chunk()
            return CreateChunkState()

        # aumenetar en uno porque se va a chunkear la clase desde sus funciones -> pasar a la primera función de la clase
        context.next_definition_index += 1
        context.class_next_definition_index = 0
        
        return ProcessClassState()
    
class ProcessClassState(ChunkingState):
    """
    Utilizar la misma técnica que para las funciones
    Si las funciones de clase se han acabado volver al estado anterior
    """
    def handle(self, context):
        if context.current_class_definition_is_last():
            return EmptyChunkState()

        if context.next_definition_should_be_added_to_current_chunk():
            context.add_next_definition_to_current_chunk()
            context.class_next_definition_index += 1
            context.add_remaining_lines_to_chunk_if_last_definition()


            # Si es la última definición del fichero, crear la clase
            if context.current_definition_is_last():
                context.create_chunk()

            return ProcessClassState()
        else:
            return CreateClassChunkState()

class CreateClassChunkState(ChunkingState):
    def handle(self, context):
        """
        Igual que el otro create chunk, pero para la clase
        """
        context.create_chunk()

        return ProcessClassState()

class AddLastLinesState(ChunkingState):
    def handle(self, context):
        """
        Añadir las últimas líneas al chunk actual
        """
        if context.create_last_chunk:
            context.chunk_end_line = context.file_line_size
            context.create_chunk()
        return FinalState()
        
class FinalState(ChunkingState):
    def handle(self, context):
        return self