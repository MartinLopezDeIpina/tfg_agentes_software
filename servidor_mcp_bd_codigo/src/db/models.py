from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, create_engine, Boolean
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship
from sqlalchemy import func

"""
La base de datos implementa un Closure Table para almacenar la jerarquía de directorios y archivos.
Los archivos se almacenan en la tabla fsentries, y los chunks de archivos se almacenan en la tabla file_chunks.

La tabla Ancestors almacena todas las relaciones de ancestros y descendientes entre los fsentries. Por ejemplo, el directorio
root tendrá todos los archivos y directorios como descendientes, y todos los archivos y directorios tendrán a root como ancestro.
Esta tabla repite las relaciones, pero la consulta para obtener los chunks dentro de un directorio se hace directamente con un join.
"""

Base = declarative_base()

class FSEntry(Base):
    __tablename__ = 'fsentry'

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    parent_id = Column(Integer, ForeignKey('fsentries.id'), nullable=True)
    is_directory = Column(Boolean, nullable=False)

    children = relationship("FSEntry",
                           backref="parent",
                           remote_side=[id],
                           cascade="all, delete-orphan")

    descendants = relationship("Ancestor",
                              foreign_keys="Ancestor.ancestor_id",
                              backref="ancestor_entry")

    ancestors = relationship("Ancestor",
                            foreign_keys="Ancestor.descendant_id",
                            backref="descendant_entry")

    chunks = relationship("FileChunk", backref="file")

    def __init__(self, name, parent_id, is_directory):
        self.name = name
        self.is_directory = is_directory
        self.parent_id = parent_id


class Ancestor(Base):
    __tablename__ = 'ancestors'

    descendant_id = Column(Integer, ForeignKey('fsentries.id'), primary_key=True)
    ancestor_id = Column(Integer, ForeignKey('fsentries.id'), primary_key=True)
    depth = Column(Integer, nullable=False)

class FileChunk(Base):
    __tablename__ = 'file_chunks'

    chunk_id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey('fsentries.id'))
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)
    embedding = Column(Vector(1536))

    def __init__(self, file_id: int, start_line: int, end_line: int):
        self.file_id = file_id
        self.start_line = start_line
        self.end_line = end_line
