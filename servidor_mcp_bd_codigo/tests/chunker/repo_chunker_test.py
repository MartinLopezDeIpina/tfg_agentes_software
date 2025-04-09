import os
import sys
from pathlib import Path

from unittest.mock import patch, MagicMock
from tree_sitter import Point

from chunker.chunk_objects import Definition
from src.chunker.repo_chunker import analyze_file_abstract_syntaxis_tree
from utils.utils import get_file_absolute_path, get_file_text
from src.chunker.repo_chunker import FileChunker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from config import TEST_EXAMPLE_FILES_PATH

def return_definition_extraction(example_file_path):
    """
    Se realiza un mock de la función files de importlib.resources, ya que el módulo de test
    es diferente al módulo de la aplicación.
    @param example_file_path: nombre del fichero de ejemplo
    @return: lista de definiciones calculadas con el código a probar
    """
    with patch('importlib.resources.files') as mock_files:

        #todo: no depender de la ruta absoluta
        mock_files.return_value = Path('/home/martin/tfg_agentes_software/servidor_mcp_bd_codigo')

        file_relative_path = os.path.join(TEST_EXAMPLE_FILES_PATH, example_file_path)
        absolute_file_path = get_file_absolute_path(file_relative_path)
        file_content = get_file_text(absolute_file_path)

        tree_captures = analyze_file_abstract_syntaxis_tree(file_content, absolute_file_path)
        file_chunker = FileChunker()

        definitions = file_chunker.get_definitions_from_tree_captures(tree_captures)
        return definitions

def assert_definitions_equal(actual_definitions, expected_definitions):
    assert len(actual_definitions) == len(expected_definitions)

    assert len(actual_definitions) == len(expected_definitions)
    for actual, expected in zip(actual_definitions, expected_definitions):
        assert actual.name == expected.name
        assert actual.start_point.row == expected.start_point.row
        assert actual.end_point.row == expected.end_point.row
        assert actual.is_class == expected.is_class


def test_definition_extraction_python():
    """
    Comprueba la correta anotación de funciones y clases en el fichero example_files/PGVectorTools.py
    """
    file_path = "PGVectorTools.py"
    expected_definitions = [
        Definition(
            name="PGVectorTools",
            start_point=Point(row=13, column=0),
            end_point=Point(row=174, column=24),
            is_class=True
        ),
        Definition(
            name="__init__",
            start_point=Point(row=14, column=4),
            end_point=Point(row=17, column=20),
            is_class=False
        ),
        Definition(
            name="create_pgvector_table",
            start_point=Point(row=19, column=4),
            end_point=Point(row=33, column=27),
            is_class=False
        ),
        Definition(
            name="index_resource",
            start_point=Point(row=35, column=4),
            end_point=Point(row=52, column=40),
            is_class=False
        ),
        Definition(
            name="delete_resource",
            start_point=Point(row=54, column=4),
            end_point=Point(row=69, column=42),
            is_class=False
        ),
        Definition(
            name="search_similar_resources",
            start_point=Point(row=72, column=4),
            end_point=Point(row=163, column=22),
            is_class=False
        ),
        Definition(
            name="get_pgvector_retriever",
            start_point=Point(row=165, column=4),
            end_point=Point(row=174, column=24),
            is_class=False
        )
    ]
    actual_definitions = return_definition_extraction(file_path)
    assert_definitions_equal(actual_definitions, expected_definitions)

def test_definition_extraction_java_script():
    """
    Comprueba la correta anotación de funciones y clases en el fichero example_files/example_javascript.py
    El parser de javascript no funciona correctamente, por lo que se ha configurado el fichero de query
    para extraer las clases unicamente.
    """
    file_path = "example_javascript.js"
    expected_definitions = [
        Definition(
            name="PlaceholderClass",
            start_point=Point(row=54, column=0),
            end_point=Point(row=75, column=24),
            is_class=True
        ),
        ]

    actual_definitions = return_definition_extraction(file_path)
    assert_definitions_equal(actual_definitions, expected_definitions)



