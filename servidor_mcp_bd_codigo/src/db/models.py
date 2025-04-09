from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Table, Integer, String, ForeignKey, DateTime, Text, create_engine, Boolean
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship, backref
from sqlalchemy import func

from src.db.db_connection import DBConnection

"""
La base de datos implementa un Closure Table para almacenar la jerarquía de directorios y archivos.
Los archivos se almacenan en la tabla fsentry, y los chunks de archivos se almacenan en la tabla file_chunks.
La tabla Ancestors almacena todas las relaciones de ancestros y descendientes entre los fsentry. Por ejemplo, el directorio
root tendrá todos los archivos y directorios como descendientes, y todos los archivos y directorios tendrán a root como ancestro.
Esta tabla repite las relaciones, pero la consulta para obtener los chunks dentro de un directorio se hace directamente con un join.
"""
Base = declarative_base()

class FSEntry(Base):
    __tablename__ = 'fsentry'
    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    parent_id = Column(Integer, ForeignKey('fsentry.id'), nullable=True)
    is_directory = Column(Boolean, nullable=False)
    path = Column(Text, nullable=False)

    children = relationship(
        "FSEntry",
        backref=backref("parent", remote_side=[id]),
        cascade="all, delete-orphan",
        collection_class=list
    )

    descendants = relationship(
        "Ancestor",
        foreign_keys="Ancestor.ancestor_id",
        backref="ancestor_entry"
    )

    ancestors = relationship(
        "Ancestor",
        foreign_keys="Ancestor.descendant_id",
        backref="descendant_entry"
    )

    chunks = relationship("FileChunk", backref="file")

    def __init__(self, name, parent_id, is_directory, path):
        self.name = name
        self.is_directory = is_directory
        self.parent_id = parent_id
        self.path = path

class Ancestor(Base):
    __tablename__ = 'ancestors'
    descendant_id = Column(Integer, ForeignKey('fsentry.id'), primary_key=True)
    ancestor_id = Column(Integer, ForeignKey('fsentry.id'), primary_key=True)
    depth = Column(Integer, nullable=False)

chunk_references = Table(
    'chunk_references',
    Base.metadata,
    Column('referencing_id', Integer, ForeignKey('file_chunks.chunk_id'), primary_key=True),
    Column('referenced_id', Integer, ForeignKey('file_chunks.chunk_id'), primary_key=True)
)

class FileChunk(Base):
    __tablename__ = 'file_chunks'
    chunk_id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey('fsentry.id'))
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)
    embedding = Column(Vector(1536))
    docs = Column(Text)
    """
    chunk_x.referenced_chunks: Los chunks destino (a los que X apunta)
    chunk_x.referencing_chunks: Los chunks origen (que apuntan a X)
    """
    referenced_chunks = relationship(
        "FileChunk",
        secondary=chunk_references,
        primaryjoin=(chunk_id == chunk_references.c.referencing_id),
        secondaryjoin=(chunk_id == chunk_references.c.referenced_id),
        backref="referencing_chunks"
    )

    def __init__(self, file_id: int, start_line: int, end_line: int):
        self.file_id = file_id
        self.start_line = start_line
        self.end_line = end_line

engine = DBConnection.get_engine()
Base.metadata.create_all(engine)