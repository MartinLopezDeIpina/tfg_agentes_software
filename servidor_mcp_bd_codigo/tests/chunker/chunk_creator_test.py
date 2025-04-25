from src.chunker.chunk_creator import ChunkCreator
from src.db.models import FileChunk

from unittest.mock import MagicMock
import pytest

class TestChunkReferences:
    @pytest.fixture
    def setup_mocks(self):
        """Configuración común para los tests de referencias entre chunks."""
        mock_session = MagicMock()
        creator = ChunkCreator(mock_session)
        return mock_session, creator

    def test_add_chunk_references_to_db_simple_case(self, setup_mocks):
        """Test para el caso simple con referencias resueltas."""
        mock_session, creator = setup_mocks

        chunk = MagicMock(spec=FileChunk)
        chunk.chunk_id = 1
        chunk.referencing_chunks = []
        chunk.referenced_chunks = []

        definition_chunk = MagicMock(spec=FileChunk)
        definition_chunk.chunk_id = 2
        definition_chunk.referencing_chunks = []
        definition_chunk.referenced_chunks = []

        creator.solved_references = {1: ["reference_name"]}
        creator.name_definitions = {"reference_name": [2]}
        creator.not_solved_references = {}

        mock_session.query.return_value.filter.return_value.one.side_effect = [chunk, definition_chunk]

        creator.add_chunk_references_to_db()

        assert definition_chunk in chunk.referenced_chunks
        assert len(chunk.referenced_chunks) == 1

    def test_add_chunk_references_to_db_not_solved_reference(self, setup_mocks):
        """Test para el caso simple con referencias no resueltas."""
        mock_session, creator = setup_mocks

        chunk = MagicMock(spec=FileChunk)
        chunk.chunk_id = 1
        chunk.referencing_chunks = []
        chunk.referenced_chunks = []

        definition_chunk = MagicMock(spec=FileChunk)
        definition_chunk.chunk_id = 2
        definition_chunk.referencing_chunks = []
        definition_chunk.referenced_chunks = []

        creator.solved_references = {}
        creator.name_definitions = {"reference_name": [2]}
        creator.not_solved_references = {1: ["reference_name"]}

        mock_session.query.return_value.filter.return_value.one.side_effect = [chunk, definition_chunk]

        creator.solve_unsolved_references()
        creator.add_chunk_references_to_db()

        assert definition_chunk in chunk.referenced_chunks
        assert len(chunk.referenced_chunks) == 1

    def test_mixed_references(self, setup_mocks):
        """
        Test para caso con 3 chunks, A, B y C. Cada uno una definición, defA, defB y defC.

        ChunkA tiene una referencia a defB.
        ChunkB tiene una referencia a defA.
        ChunkC tiene una referencia a defB.

        Las referencias ChunkA->defB y ChunkB->defA están resueltas.
        La referencia ChunkC->defB no está resuelta.
        """
        mock_session, creator = setup_mocks

        chunk_a = MagicMock(spec=FileChunk)
        chunk_a.chunk_id = 1

        chunk_b = MagicMock(spec=FileChunk)
        chunk_b.chunk_id = 2

        chunk_c = MagicMock(spec=FileChunk)
        chunk_c.chunk_id = 3

        chunk_a.referenced_chunks = [chunk_b]
        chunk_a.referencing_chunks = []
        chunk_b.referenced_chunks = [chunk_a]
        chunk_b.referencing_chunks = []
        # no resolver la dependencia
        chunk_c.referenced_chunks = []
        chunk_c.referencing_chunks = []

        creator.name_definitions = {
            "defA": [1],
            "defB": [2],
            "defC": [3]
        }
        creator.solved_references = {
            1: ["defB"],
            2: ["defA"]
        }
        creator.not_solved_references = {
            3: ["defB"]
        }

        mock_session.query.return_value.filter.return_value.one.side_effect = [
            chunk_a, chunk_b, chunk_b, chunk_a, chunk_c, chunk_b
        ]

        creator.solve_unsolved_references()
        creator.add_chunk_references_to_db()

        assert chunk_b in chunk_a.referenced_chunks
        assert len(chunk_a.referenced_chunks) == 1

        assert chunk_a in chunk_b.referenced_chunks
        assert len(chunk_b.referenced_chunks) == 1

        assert chunk_b in chunk_c.referenced_chunks
        assert len(chunk_c.referenced_chunks) == 1

        assert chunk_a not in chunk_a.referenced_chunks
        assert chunk_b not in chunk_b.referenced_chunks
        assert chunk_c not in chunk_c.referenced_chunks



