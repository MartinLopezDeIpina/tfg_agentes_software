import pytest
from unittest.mock import Mock, MagicMock, call
from dataclasses import dataclass

from src.chunker.chunk_creator import ChunkCreator
from src.chunker.file_chunk_state import (
    ChunkingContext, StartState, EmptyChunkState,
    FullChunkState, CreateChunkState, BigChunkState,
    ProcessClassState, FinalState
)


@dataclass
class Point:
    row: int
    col: int


@dataclass
class Definition:
    id: str
    type: str
    start_point: Point
    end_point: Point

    def __str__(self):
        return f"{self.id} ({self.type})"


@pytest.fixture
def chunk_creator():
    """Mock de ChunkCreator para rastrear llamadas a sus métodos"""
    creator = Mock(spec=ChunkCreator)
    creator.chunk_max_line_size = 100
    creator.minimum_proportion = 0.2
    creator.create_chunk = MagicMock()
    creator.create_multiple_chunks = MagicMock()
    return creator


@pytest.fixture
def function_definitions_model_tools():
    return [
        Definition(
            id="function1",
            type="function_definition",
            start_point=Point(row=21, col=0),
            end_point=Point(row=23, col=39)
        ),
        Definition(
            id="function2",
            type="function_definition",
            start_point=Point(row=26, col=0),
            end_point=Point(row=46, col=30)
        ),
        Definition(
            id="function3",
            type="function_definition",
            start_point=Point(row=48, col=0),
            end_point=Point(row=80, col=30)
        ),
        Definition(
            id="function4",
            type="function_definition",
            start_point=Point(row=83, col=0),
            end_point=Point(row=128, col=27)
        ),
        Definition(
            id="function5",
            type="function_definition",
            start_point=Point(row=130, col=0),
            end_point=Point(row=132, col=15)
        ),
        Definition(
            id="function6",
            type="function_definition",
            start_point=Point(row=134, col=0),
            end_point=Point(row=230, col=15)
        ),
        Definition(
            id="function7",
            type="function_definition",
            start_point=Point(row=232, col=0),
            end_point=Point(row=315, col=15)
        ),
        Definition(
            id="function7",
            type="function_definition",
            start_point=Point(row=318, col=0),
            end_point=Point(row=321, col=15)
        )
    ]


@pytest.fixture
def make_context(chunk_creator):
    """Fábrica para crear contextos con diferentes definiciones y parámetros"""

    def _make_context(definitions, file_line_size=128, references=None,
                      chunk_max_size=None, chunk_min_proportion=None):
        if references is None:
            references = []

        # Configurar el chunk_creator si se proporcionan valores
        if chunk_max_size is not None:
            chunk_creator.chunk_max_line_size = chunk_max_size

        if chunk_min_proportion is not None:
            chunk_creator.minimum_proportion = chunk_min_proportion

        return ChunkingContext(
            chunk_creator=chunk_creator,
            definitions=definitions,
            references=references,
            file_line_size=file_line_size,
            file_id=33
        )

    return _make_context


def verificar_llamadas(chunk_creator, expected_create_chunk_calls, expected_create_multiple_chunks_calls):
    """Verifica que las llamadas realizadas al chunk_creator coincidan con las esperadas"""
    assert chunk_creator.create_chunk.call_count == len(expected_create_chunk_calls), \
        f"Expected {len(expected_create_chunk_calls)} calls to create_chunk, got {chunk_creator.create_chunk.call_count}"

    chunk_creator.create_chunk.assert_has_calls(expected_create_chunk_calls, any_order=False)

    assert chunk_creator.create_multiple_chunks.call_count == len(expected_create_multiple_chunks_calls), \
        f"Expected {len(expected_create_multiple_chunks_calls)} calls to create_multiple_chunks, got {chunk_creator.create_multiple_chunks.call_count}"
    chunk_creator.create_multiple_chunks.assert_has_calls(expected_create_multiple_chunks_calls, any_order=False)

    # Para depuración, si el test falla, muestra las llamadas reales que se hicieron
    if chunk_creator.create_chunk.call_count != len(expected_create_chunk_calls) or \
            chunk_creator.create_multiple_chunks.call_count != len(expected_create_multiple_chunks_calls):
        print("Actual create_chunk calls:")
        for i, actual_call in enumerate(chunk_creator.create_chunk.call_args_list):
            print(f"  Call {i + 1}: {actual_call}")

        print("Actual create_multiple_chunks calls:")
        for i, actual_call in enumerate(chunk_creator.create_multiple_chunks.call_args_list):
            print(f"  Call {i + 1}: {actual_call}")


class TestFunctionChunks:
    def test_chunks_creation_custom_config(self, make_context, function_definitions_model_tools, chunk_creator):
        # Reinicializar el mock para asegurar que no haya llamadas anteriores
        chunk_creator.create_chunk.reset_mock()
        chunk_creator.create_multiple_chunks.reset_mock()

        context = make_context(
            definitions=function_definitions_model_tools,
            file_line_size=322,
            chunk_max_size=50,
            chunk_min_proportion=0.4
        )

        state = StartState()
        while not isinstance(state, FinalState):
            state = state.handle(context)

        expected_create_chunk_calls = [
            call(
                chunk_start_line=0,
                chunk_end_line=46,
                definitions=function_definitions_model_tools,
                references=[],
                file_id=33
            ),
            call(
                chunk_start_line=46,
                chunk_end_line=80,
                definitions=function_definitions_model_tools,
                references=[],
                file_id=33
            ),
            call(
                chunk_start_line=80,
                chunk_end_line=128,
                definitions=function_definitions_model_tools,
                references=[],
                file_id=33
            ),
        ]

        expected_create_multiple_chunks_calls = [
            #Caso en el que la siguiente función no cabe en el chunk pero el chunk actual es demasiado pequeño
            call(
                chunk_start_line=128,
                chunk_end_line=230,
                definitions=function_definitions_model_tools,
                references=[],
                file_id=33
            ),
            #Caso en el que la siguiente función no cabe en el chunk, pero se añade la última porque sino el úlitmo chunk es demasiado pequeño
            call(
                chunk_start_line=230,
                chunk_end_line=321,
                definitions=function_definitions_model_tools,
                references=[],
                file_id=33
            )
        ]

        verificar_llamadas(chunk_creator, expected_create_chunk_calls, expected_create_multiple_chunks_calls)
"""


@pytest.fixture
def class_definition():
   #Crea una definición de clase para testing
    return Definition(
        id="class1",
        type="class_definition",
        start_point=Point(row=40, col=0),
        end_point=Point(row=60, col=0)
    )


@pytest.fixture
def mixed_definitions(function_definitions, class_definition):
    #Mezcla funciones y clases
    return function_definitions + [class_definition]




@pytest.fixture
def context_with_mixed(chunk_creator, mixed_definitions):
    Contexto con funciones y clases
    return ChunkingContext(
        chunk_creator=chunk_creator,
        definitions=mixed_definitions,
        references=[],
        code_text="# Código mixto de ejemplo\n",
        file_id="test_mixed.py"
    )



# Tests para los diferentes estados
class TestStartState:
    def test_initial_transition(self, context_with_functions):
        state = StartState()
        next_state = state.handle(context_with_functions)

        # Verifica que el estado inicial configura las líneas adecuadamente
        assert context_with_functions.chunk_end_line == 4  # Justo antes de la primera definición
        # Verifica la transición correcta de estado
        assert isinstance(next_state, EmptyChunkState)


class TestEmptyChunkState:
    def test_add_definition_to_chunk(self, context_with_functions):
        # Configura el contexto como si ya hubiera pasado por StartState
        context_with_functions.chunk_end_line = 4

        state = EmptyChunkState()
        next_state = state.handle(context_with_functions)

        # Verifica que se añadió la primera definición al chunk
        assert len(context_with_functions.current_chunk_definitions) == 1
        assert context_with_functions.next_definition_index == 1
        assert context_with_functions.chunk_end_line == 8  # Fin de la primera función


class TestFullChunkState:
    def test_transition_to_create_chunk(self, context_with_functions):
        # Configura el contexto como si ya tuviera definiciones
        context_with_functions.current_chunk_definitions = [context_with_functions.definitions[0]]

        state = FullChunkState()
        next_state = state.handle(context_with_functions)

        # Verifica la transición correcta
        assert isinstance(next_state, CreateChunkState)

    def test_transition_to_big_chunk(self, context_with_functions):
        # Asegura que no hay definiciones en el chunk actual
        context_with_functions.current_chunk_definitions = []

        state = FullChunkState()
        next_state = state.handle(context_with_functions)

        # Verifica la transición a BigChunkState
        assert isinstance(next_state, BigChunkState)


class TestCreateChunkState:
    def test_create_single_chunk(self, context_with_functions):
        # Configura el contexto
        context_with_functions.chunk_start_line = 0
        context_with_functions.chunk_end_line = 8
        context_with_functions.current_chunk_definitions = [context_with_functions.definitions[0]]

        state = CreateChunkState()
        next_state = state.handle(context_with_functions)

        # Verifica que se llamó a create_chunk con los parámetros correctos
        context_with_functions.chunk_creator.create_chunk.assert_called_once_with(
            chunk_start_line=0,
            chunk_end_line=8,
            definitions=context_with_functions.definitions,
            references=[],
            file_id="test_file.py"
        )

        # Verifica que se reiniciaron las variables del contexto
        assert context_with_functions.current_chunk_definitions == []
        assert context_with_functions.chunk_start_line == 8

        # Verifica la transición correcta
        assert isinstance(next_state, EmptyChunkState)

    def test_create_multiple_chunks(self, context_with_functions):
        # Configura el contexto con un chunk que excede el tamaño máximo
        context_with_functions.chunk_start_line = 0
        context_with_functions.chunk_end_line = 35  # Mayor que chunk_max_line_size (10)
        context_with_functions.current_chunk_definitions = [context_with_functions.definitions[2]]  # Función grande

        state = CreateChunkState()
        next_state = state.handle(context_with_functions)

        # Verifica que se llamó a create_multiple_chunks
        context_with_functions.chunk_creator.create_multiple_chunks.assert_called_once_with(
            chunk_start_line=0,
            chunk_end_line=35,
            definitions=context_with_functions.definitions,
            references=[],
            file_id="test_file.py"
        )

        # Verifica la transición correcta
        assert isinstance(next_state, EmptyChunkState)


class TestBigChunkState:
    def test_handle_big_function(self, context_with_functions):
        # Configura el contexto para apuntar a una función grande
        context_with_functions.next_definition_index = 2  # La tercera función (grande)

        state = BigChunkState()
        next_state = state.handle(context_with_functions)

        # Verifica que se añadió la función al chunk actual
        assert len(context_with_functions.current_chunk_definitions) == 1
        assert context_with_functions.current_chunk_definitions[0].id == "func3"

        # Verifica la transición a CreateChunkState
        assert isinstance(next_state, CreateChunkState)

    def test_handle_class(self, context_with_mixed):
        # Configura el contexto para apuntar a una clase
        context_with_mixed.next_definition_index = 3  # La definición de clase

        state = BigChunkState()
        next_state = state.handle(context_with_mixed)

        # Verifica la transición a ProcessClassState para procesar la clase
        assert isinstance(next_state, ProcessClassState)


# Test de integración para probar todo el flujo
def test_complete_chunking_flow(context_with_functions):
    # Comienza con StartState
    state = StartState()

    # Procesa hasta llegar a FinalState
    while not isinstance(state, FinalState):
        state = state.handle(context_with_functions)

    # Verifica que se llamó a los métodos de creación de chunks
    assert context_with_functions.chunk_creator.create_chunk.call_count > 0

    # Verifica que todos los chunks fueron procesados
    assert context_with_functions.finished is True


# Test con un archivo "real"
def test_with_example_file():
    # Define un mock de ChunkCreator
    chunk_creator = Mock(spec=ChunkCreator)
    chunk_creator.chunk_max_line_size = 15
    chunk_creator.create_chunk = MagicMock()
    chunk_creator.create_multiple_chunks = MagicMock()

    # Simula el proceso de parseo de un archivo real
    # creando las definiciones manualmente
    definitions = [
        Definition(
            id="sum_numbers",
            type="function_definition",
            start_point=Point(row=2, col=0),
            end_point=Point(row=5, col=0)
        ),
        Definition(
            id="Calculator",
            type="class_definition",
            start_point=Point(row=8, col=0),
            end_point=Point(row=25, col=0)
        ),
        # Métodos dentro de la clase Calculator
        Definition(
            id="Calculator.add",
            type="function_definition",
            start_point=Point(row=10, col=4),
            end_point=Point(row=12, col=4)
        ),
        Definition(
            id="Calculator.subtract",
            type="function_definition",
            start_point=Point(row=14, col=4),
            end_point=Point(row=16, col=4)
        ),
        Definition(
            id="Calculator.multiply",
            type="function_definition",
            start_point=Point(row=18, col=4),
            end_point=Point(row=20, col=4)
        ),
        Definition(
            id="Calculator.divide",
            type="function_definition",
            start_point=Point(row=22, col=4),
            end_point=Point(row=24, col=4)
        ),
        Definition(
            id="main",
            type="function_definition",
            start_point=Point(row=28, col=0),
            end_point=Point(row=35, col=0)
        )
    ]

    # Crea el contexto
    context = ChunkingContext(
        chunk_creator=chunk_creator,
        definitions=definitions,
        references=[],  # Simplificamos sin referencias
        code_text="# Código de ejemplo simulado\n",
        file_id="example.py"
    )

    # Ejecuta la máquina de estados
    state = StartState()
    while not isinstance(state, FinalState):
        state = state.handle(context)

    # Verifica que se crearon los chunks esperados
    expected_calls = [
        # Primer chunk: comentarios iniciales hasta antes de la primera función
        Mock.call(chunk_start_line=0, chunk_end_line=1, definitions=definitions, references=[], file_id="example.py"),
        # Segundo chunk: primera función
        Mock.call(chunk_start_line=1, chunk_end_line=5, definitions=definitions, references=[], file_id="example.py"),
        # Siguiente chunk podría ser la clase completa o dividida en partes
        # Las llamadas exactas dependerán de la implementación específica
    ]

    # Verifica que se han hecho al menos algunas llamadas a create_chunk
    assert chunk_creator.create_chunk.call_count > 0

    # Si la clase es demasiado grande, debería llamarse a create_multiple_chunks
    if chunk_creator.create_multiple_chunks.call_count > 0:
        # Verifica que se llamó con la clase
        chunk_creator.create_multiple_chunks.assert_any_call(
            chunk_start_line=8,
            chunk_end_line=25,
            definitions=definitions,
            references=[],
            file_id="example.py"
        )
"""