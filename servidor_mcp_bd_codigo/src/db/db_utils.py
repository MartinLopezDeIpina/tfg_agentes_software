from src.db.models import FSEntry, Ancestor


def add_fs_entry(session, name: str, parent_id: int, is_directory: bool):
    """
    Añade un nuevo archivo o directorio al sistema de archivos y gestiona automáticamente
    todas las relaciones en la tabla de ancestros.

    Returns:
        La nueva instancia de FSEntry con ID asignado
    """

    entry = FSEntry(name=name, parent_id=parent_id, is_directory=is_directory)
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

