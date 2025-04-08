import contextlib
from typing import List
import os
from treelib import Tree
import io
from config import TREE_STR_IGNORE_DIRS


def add_nodes(tree: Tree, directory: str, parent: str, repo_path: str, ignored_dirs: List[str] = None, ignored_files: List[str] = None):
    """
    Añade nodos al árbol de forma recursiva.

    Args:
        tree: Objeto Tree donde se añadirán los nodos
        directory: Directorio actual a procesar
        parent: ID del nodo padre
        repo_path: Ruta base del repositorio
        ignored_dirs: Lista de directorios a ignorar
        ignored_files: Lista de archivos a ignorar
    """
    if ignored_dirs is None:
        ignored_dirs = []
    if ignored_files is None:
        ignored_files = []

    try:
        # Listar directorios y archivos
        items = os.listdir(directory)
        # Procesar primero directorios, luego archivos (para mejor visualización)
        dirs = [item for item in items if os.path.isdir(os.path.join(directory, item)) and item not in ignored_dirs]
        files = [item for item in items if
                 os.path.isfile(os.path.join(directory, item)) and item not in ignored_files]

        # Ordenar alfabéticamente
        dirs.sort()
        files.sort()

        for dir_name in dirs:
            dir_path = os.path.join(directory, dir_name)
            # El ID del nodo debe ser único -> usar ruta relativa por si dos directorios tienen el mismo nombre
            node_id = os.path.relpath(dir_path, repo_path)

            # Crear nodo directorio y añadir hijos recursivamente
            tree.create_node(dir_name, node_id, parent=parent)
            add_nodes(tree, dir_path, node_id, repo_path, ignored_dirs, ignored_files)

        for file_name in files:
            file_path = os.path.join(directory, file_name)
            node_id = os.path.relpath(file_path, repo_path)

            tree.create_node(file_name, node_id, parent=parent)

    except PermissionError:
        print(f"Permiso denegado para acceder a {directory}")


def generate_repo_tree(repo_path: str, ignored_dirs: List[str] = None, ignored_files: List[str] = None):
    """
    Genera un árbol de la estructura de directorios de un repositorio.

    Args:
        repo_path: Ruta al repositorio
        ignored_dirs: Lista de directorios a ignorar
        ignored_files: Lista de archivos a ignorar

    Returns:
        Tree: Objeto Tree de treelib con la estructura del repositorio
    """
    if ignored_dirs is None:
        ignored_dirs = []
    if ignored_files is None:
        ignored_files = []

    try:
        tree = Tree()
        root_name = os.path.basename(os.path.abspath(repo_path))
        tree.create_node(root_name, root_name)
    except FileNotFoundError or PermissionError:
        print(f"Error: No se puede acceder a la ruta {repo_path}")
        return None

    # Iniciar recursión
    add_nodes(tree, repo_path, root_name, repo_path, ignored_dirs, ignored_files)

    return tree

def generate_repo_tree_str(repo_path: str):

    tree = generate_repo_tree(
        repo_path,
        ignored_dirs=TREE_STR_IGNORE_DIRS,
        ignored_files=[]
    )
    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        tree.show()

    repo_tree_str = f.getvalue()

    return repo_tree_str

if __name__ == "__main__":
    target_path = "/home/martin/open_source/ia-core-tools/app/static/vendor"
    print(f"Generando árbol de repositorio para: {target_path}")

    # Generar y mostrar el árbol
    repo_tree = generate_repo_tree(
        target_path,
        ignored_dirs=[],
        ignored_files=[]
    )

    repo_tree.show()

    print("\nÁrbol generado correctamente.")