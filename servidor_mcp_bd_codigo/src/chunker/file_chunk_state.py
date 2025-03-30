from abc import ABC, abstractmethod

from src.chunker.chunk_creator import ChunkCreator

class ChunkingContext:
    def __init__(self, chunk_creator: ChunkCreator, definitions, references, code_text, file_id):
        self.chunk_creator = chunk_creator
        self.definitions = definitions
        self.references = references
        self.code_text = code_text
        self.file_id = file_id
        self.chunk_max_line_size = chunk_creator.chunk_max_line_size

        # Variables de estado
        self.chunk_start_line = 0
        self.chunk_end_line = 0
        self.finished = False
        self.current_chunk_definitions = []
        # Índice de definición a evaluar, sin estar en el chunk
        self.next_definition_index = -1

        # Variables para el procesamiento de clases
        self.class_definitions = []
        self.class_next_definition_index = -1
    
    def add_next_definition_to_current_chunk(self):
        next_definition = self.definitions[self.next_definition_index]
        self.current_chunk_definitions.append(next_definition)
        self.chunk_end_line = next_definition.end_point.row
        self.next_definition_index += 1
    
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
        first_definition_start = context.definitions[0].start_point.row
        context.chunk_end_line = first_definition_start - 1
        
        if len(context.definitions) == 0:
            # Si no hay definiciones usar un simple chunk lanzando excepción
            raise ValueError("No definitions found in the file.")
            
        return EmptyChunkState()

class EmptyChunkState(ChunkingState):
    def handle(self, context):
        if context.chunk_end_line >= context.chunk_max_line_size:
            context.finished = True
        if context.finished:
            return FinalState()
        
        context.next_definition_index += 1
        # todo: cuando llega a la última definición esto da out of range porque aumenta el contador
        next_definition = context.definitions[context.next_definition_index]
        # Considerar las líneas entre el final del chunk actual y el inicio de la siguiente definición como parte de la siguiente definición
        next_definition_line_size = next_definition.end_point.row - context.chunk_end_line
        current_chunk_size = context.chunk_end_line - context.chunk_start_line
        
        # si la definición cabe en el chunk actual añadirla y repetir
        if next_definition_line_size + current_chunk_size <= context.chunk_max_line_size:
            context.add_next_definition_to_current_chunk()
            
            # Si es la última definición, crear el chunk
            if context.next_definition_index >= len(context.definitions):
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
        next_definition = context.definitions[context.next_definition_index]
        
        """
        Si la definición es una función, dividirla en múltiples chunks
        Si es una clase, procesarla internamente con sus funciones
        """
        if str(next_definition.type) == "function_definition":
            context.add_next_definition_to_current_chunk()
            return CreateChunkState()
        else:
            # Es una clase, procesarla internamente
            return ProcessClassState()

class CreateChunkState(ChunkingState):
    """
    Crea un chunk con las definiciones acumuladas en el contexto.
    Si el chunk supera el tamaño máximo, se divide en múltiples chunks.
    """
    def handle(self, context):
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
            and defi.id != class_definition.id
        ]
        context.class_next_definition_index = 0
        
        return ProcessClassState()
    
class ProcessClassState(ChunkingState):
    """
    Añadir la siguiente definición y evaluar si cabe en el chunk
    
    """
    def handle(self, context):
        if context.class_next_definition_index >= len(context.class_definitions):
            # No hay más definiciones de clase
            return EmptyChunkState()
        
        current_class_definition = context.class_definitions[context.class_next_definition_index]
        
        """
        Si la definición cabe en el chunk actual añadirla, si no, crear el chunk
        """
        chunk_size = current_class_definition.end_point.row - context.chunk_start_line
        if chunk_size <= context.chunk_max_line_size:
            context.class_definitions.append(current_class_definition)
            context.class_next_definition_index += 1
            
            return ProcessClassState()
        else:
            return CreateClassChunkState()

class CreateClassChunkState(ChunkingState):
    def handle(self, context):
        """
        Crea un chunk con las definiciones acumuladas en el contexto.
        Si el chunk supera el tamaño máximo, se divide en múltiples chunks.
        """
        context.create_chunk()

        return EmptyChunkState()
        
class FinalState(ChunkingState):
    def handle(self, context):
        return self