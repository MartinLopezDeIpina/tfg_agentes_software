import os

from src.db.db_connection import DBConnection
from src.db.models import FSEntry, Ancestor, FileChunk
from sqlalchemy.orm import Session
from src.utils.utils import get_file_text, get_start_to_end_lines_from_text_code
from config import REPO_ROOT_ABSOLUTE_PATH

def obtain_fsentry_relative_path(session: Session, fsentry_id: int) -> str:

    # En caso de ser el nodo raíz, devolver cadena vacía
    if fsentry_id is None:
        return ""

    fsentry = session.query(FSEntry).filter(FSEntry.id == fsentry_id).first()
    return fsentry.path

def add_fs_entry(session: Session, name: str, parent_id: int, is_directory: bool):
    """
    Añade un nuevo archivo o directorio al sistema de archivos y gestiona automáticamente
    todas las relaciones en la tabla de ancestros.

    Returns:
        La nueva instancia de FSEntry con ID asignado
    """
    if parent_id == None:
        path = ""
    else:
        parent_path = obtain_fsentry_relative_path(session, parent_id)
        path = os.path.join(parent_path, name)

    entry = FSEntry(name=name, parent_id=parent_id, is_directory=is_directory, path=path)
    session.add(entry)
    # Necesario para obtener el ID asignado
    session.flush()

    # 2. Crear relación consigo mismo (todos nodo es ancestro de sí mismo con profundidad 0)
    self_relation = Ancestor(descendant_id=entry.id, ancestor_id=entry.id, depth=0)
    session.add(self_relation)

    # 3. Si no es el nodo raíz (tiene padre), añadir relaciones con todos los ancestros del padre
    if parent_id is not None:
        # Obtener todos los ancestros del padre (incluido el padre mismo)
        parent_ancestors = session.query(Ancestor).filter(
            Ancestor.descendant_id == parent_id
        ).all()

        # Para cada ancestro del padre, crear una relación con el nuevo nodo
        new_ancestor_relations = []
        for ancestor in parent_ancestors:
            new_ancestor_relations.append(
                Ancestor(
                    descendant_id=entry.id,
                    ancestor_id=ancestor.ancestor_id,
                    depth=ancestor.depth + 1
                )
            )

        if new_ancestor_relations:
            session.add_all(new_ancestor_relations)

    session.flush()

    return entry

def get_fsentry_relative_path(fsentry: FSEntry):
    if fsentry is None:
        return ""

    session = DBConnection.get_session()
    root_node = session.query(FSEntry).filter(FSEntry.parent_id == None).first()

    # Si estamos en el nodo raíz, devolvemos cadena vacía
    if fsentry.id == root_node.id:
        return ""

    # Construir la ruta de forma recursiva
    path_parts = []
    current = fsentry

    while current is not None and current.id != root_node.id:
        path_parts.insert(0, current.name)  # Insertamos al principio para mantener el orden correcto
        current = current.parent  # Utilizamos la relación backref 'parent' para navegar hacia arriba

    return "/".join(path_parts)

def get_chunk_code(Session: Session, chunk: FileChunk, repo_path: str = REPO_ROOT_ABSOLUTE_PATH):
    chunk_file = Session.query(FSEntry).filter(FSEntry.id == chunk.file_id).first()
    chunk_file_path = os.path.join(repo_path, chunk_file.path)
    file_code = get_file_text(chunk_file_path)
    chunk_code = get_start_to_end_lines_from_text_code(file_code, chunk.start_line, chunk.end_line)
    return chunk_code

# busca el fichero sin tenenr en cuenta las mayúsulas
def get_fs_entry_from_relative_path(session: Session, relative_path: str):
    fs_entry = session.query(FSEntry).filter(
        FSEntry.path.ilike(relative_path)
    ).first()
    return fs_entry

def get_root_fs_entry(session: Session):
    root_node = session.query(FSEntry).filter(FSEntry.parent_id == None).first()
    return root_node

