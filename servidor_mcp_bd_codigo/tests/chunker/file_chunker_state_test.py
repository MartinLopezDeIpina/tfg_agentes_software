import pytest
from unittest.mock import Mock, MagicMock, call
from dataclasses import dataclass
from src.chunker.chunk_objects import Definition

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
            name="name_function1",
            start_point=Point(row=21, col=0),
            end_point=Point(row=23, col=39),
            is_class=False
        ),
        Definition(
            name="name_function2",
            start_point=Point(row=26, col=0),
            end_point=Point(row=46, col=30),
            is_class=False
        ),
        Definition(
            name="name_function3",
            start_point=Point(row=48, col=0),
            end_point=Point(row=80, col=30),
            is_class=False
        ),
        Definition(
            name="name_function4",
            start_point=Point(row=83, col=0),
            end_point=Point(row=128, col=27),
            is_class=False
        ),
        Definition(
            name="name_function5",
            start_point=Point(row=130, col=0),
            end_point=Point(row=132, col=15),
            is_class=False
        ),
        Definition(
            name="name_function6",
            start_point=Point(row=134, col=0),
            end_point=Point(row=230, col=15),
            is_class=False
        ),
        Definition(
            name="name_function7",
            start_point=Point(row=232, col=0),
            end_point=Point(row=315, col=15),
            is_class=False
        ),
        Definition(
            name="name_function8",
            start_point=Point(row=318, col=0),
            end_point=Point(row=322, col=15),
            is_class=False
        )
    ]
@pytest.fixture
def function_definitions_pg_vector_tools():
    return [
        Definition(
            name="name_class1",
            start_point=Point(row=15, col=0),
            end_point=Point(row=177, col=39),
            is_class=True
        ),
        Definition(
            name="name_function9",
            start_point=Point(row=16, col=0),
            end_point=Point(row=19, col=39),
            is_class=False
        ),
        Definition(
            name="name_function10",
            start_point=Point(row=21, col=0),
            end_point=Point(row=35, col=39),
            is_class=False
        ),
        Definition(
            name="name_function11",
            start_point=Point(row=37, col=0),
            end_point=Point(row=54, col=39),
            is_class=False
        ),
        Definition(
            name="name_function12",
            start_point=Point(row=56, col=0),
            end_point=Point(row=71, col=39),
            is_class=False
        ),
        Definition(
            name="name_function13",
            start_point=Point(row=75, col=0),
            end_point=Point(row=166, col=39),
            is_class=False
        ),
        Definition(
            name="name_function14",
            start_point=Point(row=168, col=0),
            end_point=Point(row=177, col=39),
            is_class=False
        ),
    ]
@pytest.fixture
def function_definitions_function_before_class():
    return [
        Definition(
            name="name_function15",
            start_point=Point(row=15, col=0),
            end_point=Point(row=26, col=39),
            is_class=False
        ),
        Definition(
            name="name_class2",
            start_point=Point(row=26, col=0),
            end_point=Point(row=84, col=39),
            is_class=True
        ),
        Definition(
            name="name_function16",
            start_point=Point(row=27, col=0),
            end_point=Point(row=32, col=39),
            is_class=False
        ),
        Definition(
            name="name_function17",
            start_point=Point(row=32, col=0),
            end_point=Point(row=48, col=39),
            is_class=False
        ),
        Definition(
            name="name_function18",
            start_point=Point(row=48, col=0),
            end_point=Point(row=84, col=39),
            is_class=False
        ),
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
    """
    Test para comprobar el chunking correcto de las funciones.
    -Se comprueba que si la siguiente definición es demasiado grande, pero el chunk actual es demasiado pequeño,
    se añada al chunk actual dividiendo este en varios chunks.
    -Se comprueba que si la definición siguiente no cabe en el chunk actual, pero la definición siguiente es la última
    y es demasiado pequeña para crear un chunk, se añada al chunk actual.
    """
    def test_function_chunks(self, make_context, function_definitions_model_tools, chunk_creator):
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
                chunk_end_line=322,
                definitions=function_definitions_model_tools,
                references=[],
                file_id=33
            )
        ]

        verificar_llamadas(chunk_creator, expected_create_chunk_calls, expected_create_multiple_chunks_calls)

class TestClassChunks:
    """
    Test para comprobar el chunking correcto de las clases.
    Comprueba que en el caso que la clase sea demasiado grande, el chunking se realice teniendo en cuenta sus
    funciones internas.
    """
    def test_class_chunks(self, make_context, function_definitions_pg_vector_tools, chunk_creator):
        chunk_creator.create_chunk.reset_mock()
        chunk_creator.create_multiple_chunks.reset_mock()

        context = make_context(
            definitions=function_definitions_pg_vector_tools,
            file_line_size=181,
            chunk_max_size=50,
            chunk_min_proportion=0.2
        )

        state = StartState()
        while not isinstance(state, FinalState):
            state = state.handle(context)

        expected_create_chunk_calls = [
            call(
                chunk_start_line=0,
                chunk_end_line=35,
                definitions=function_definitions_pg_vector_tools,
                references=[],
                file_id=33
            ),
            call(
                chunk_start_line=35,
                chunk_end_line=71,
                definitions=function_definitions_pg_vector_tools,
                references=[],
                file_id=33
            ),
            call(
                chunk_start_line=166,
                chunk_end_line=181,
                definitions=function_definitions_pg_vector_tools,
                references=[],
                file_id=33
            )
        ]

        expected_create_multiple_chunks_calls = [
            # Caso en el que la función dentro de la clase es demasiado grande -> se divide la función en varias, pero sólo la función de la clase
            call(
                chunk_start_line=71,
                chunk_end_line=166,
                definitions=function_definitions_pg_vector_tools,
                references=[],
                file_id=33
            ),
        ]

        verificar_llamadas(chunk_creator, expected_create_chunk_calls, expected_create_multiple_chunks_calls)

    """
    Test para comprobar que en el caso de que haya una definición de una función antes de la definición de una clase,
    y esta tiene tamaño suficiente para tener un chunk propio, se crea un chunk para la función.
    """
    def test_class_chunks_function_before_class(self, make_context, function_definitions_function_before_class, chunk_creator):
        chunk_creator.create_chunk.reset_mock()
        chunk_creator.create_multiple_chunks.reset_mock()

        context = make_context(
            definitions=function_definitions_function_before_class,
            file_line_size=84,
            chunk_max_size=50,
            chunk_min_proportion=0.2
        )

        state = StartState()
        while not isinstance(state, FinalState):
            state = state.handle(context)

        expected_create_chunk_calls = [
            call(
                chunk_start_line=0,
                chunk_end_line=26,
                definitions=function_definitions_function_before_class,
                references=[],
                file_id=33
            ),
            call(
                chunk_start_line=26,
                chunk_end_line=48,
                definitions=function_definitions_function_before_class,
                references=[],
                file_id=33
            ),
            call(
                chunk_start_line=48,
                chunk_end_line=84,
                definitions=function_definitions_function_before_class,
                references=[],
                file_id=33
            )
        ]

        expected_create_multiple_chunks_calls = []

        verificar_llamadas(chunk_creator, expected_create_chunk_calls, expected_create_multiple_chunks_calls)
