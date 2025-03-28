from typing import List
import os
from treelib import Tree

REPO_PATH = "/home/martin/open_source/ia-core-tools"

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

    tree = Tree()
    root_name = os.path.basename(os.path.abspath(repo_path))
    tree.create_node(root_name, root_name)

    # Iniciar recursión
    add_nodes(tree, repo_path, root_name, repo_path, ignored_dirs, ignored_files)

    return tree

if __name__ == "__main__":
    target_path = REPO_PATH
    print(f"Generando árbol de repositorio para: {target_path}")

    custom_ignored_dirs = ['.git', 'node_modules', '.venv', '__pycache__', 'dist', 'build']
    custom_ignored_files = ['.DS_Store', '.gitignore', '.pyc', '.pyo']

    # Generar y mostrar el árbol
    repo_tree = generate_repo_tree(
        target_path,
        ignored_dirs=custom_ignored_dirs,
        ignored_files=custom_ignored_files
    )

    repo_tree.show()

    # Si quieres guardar el árbol en un archivo
    # with open('repo_tree.txt', 'w', encoding='utf-8') as f:
    #     repo_tree.show(file=f)

    print("\nÁrbol generado correctamente.")