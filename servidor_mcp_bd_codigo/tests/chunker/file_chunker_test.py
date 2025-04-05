import os
from unittest.mock import MagicMock, patch
from chunker.repo_chunker import FileChunker
from utils.utils import get_file_absolute_path_from_path, get_file_absolute_path_from_proyect_relative_path
from src.db.models import FSEntry
#todo fix paths
from config import TEST_EXAMPLE_FILES_PATH

def create_fsentry_side_effect(created_fsentries, cls, *args, **kwargs):
    name = kwargs.get('name')
    parent_id = kwargs.get('parent_id')
    is_directory = kwargs.get('is_directory')
    path = kwargs.get('path')

    instance = MagicMock(spec=FSEntry)

    instance.name = name
    instance.parent_id = parent_id
    instance.is_directory = is_directory
    instance.path = path

    created_fsentries.append({
        'name': name,
        'parent_id': parent_id,
        'is_directory': is_directory,
        'path': path,
        'instance': instance
    })

    return instance

def test_recursive_db_repository_creation():
    created_fsentries = []
    side_effect_function = lambda cls, *args, **kwargs: create_fsentry_side_effect(created_fsentries, cls, *args, **kwargs)

    with patch('src.db.models.FSEntry.__new__', side_effect=side_effect_function):

        db_mock = MagicMock()
        test_repo_absolute_path = get_file_absolute_path_from_path('example_files/repo_directory_example')

        file_chunker = FileChunker(session=db_mock)
        file_chunker.chunk_directory_recursive(test_repo_absolute_path, None)

        expected_entry_dir_calls = [
            "repo_directory_example", "dir_a", "dir_b", "dir_c"
        ]
        expected_entry_file_calls = [
            "file_a", "file_b", "file_c", "file_d"
        ]

        for call in created_fsentries:
            if call['is_directory']:
                assert call['name'] in expected_entry_dir_calls
            else:
                assert call['name'] in expected_entry_file_calls

def test_recursive_db_repository_creation():
    created_fsentries = []
    side_effect_function = lambda cls, *args, **kwargs: create_fsentry_side_effect(created_fsentries, cls, *args, **kwargs)

    with patch('src.db.models.FSEntry.__new__', side_effect=side_effect_function):

        db_mock = MagicMock()
        test_repo_absolute_path = get_file_absolute_path_from_proyect_relative_path('tests/chunker/example_files/repo_directory_example')

        ignored_entries = [
            os.path.join(test_repo_absolute_path, "file_a"),
            os.path.join(test_repo_absolute_path, "dir_a/dir_b")
        ]
        ignored_entries = [get_file_absolute_path_from_path(entry) for entry in ignored_entries]

        file_chunker = FileChunker(session=db_mock)
        file_chunker.ignored_entries = ignored_entries
        file_chunker.chunk_directory_recursive(test_repo_absolute_path, None)

        expected_entry_dir_calls = [
            "repo_directory_example", "dir_a", "dir_b"
        ]
        expected_entry_file_calls = [
            "file_c", "file_b"
        ]

        for call in created_fsentries:
            if call['is_directory']:
                assert call['name'] in expected_entry_dir_calls
            else:
                assert call['name'] in expected_entry_file_calls
