import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

class DBConnection:
    _instance = None
    _engine = None
    DB_USER=os.getenv('DB_USER')
    DB_PASSWORD=os.getenv('DB_PASSWORD')
    DB_HOST=os.getenv('DB_HOST')
    DB_PORT=os.getenv('DB_PORT')
    DB_NAME=os.getenv('DB_NAME')

    """
    Devuelve una instancia del patrón Singleton para la conexión a la base de datos.
    
    Proporciona tanto el engine como la sesión.
    Uso: 
        db = DBConnection.get_instance()
        session = db.session
        engine = db.engine
    """
    def __init__(self):
        self.engine = create_engine(
            f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}",
            pool_size=5,
        )
        # Con el session factory y scoped session se supone que se maneja la concurrencia
        session_factory = sessionmaker(bind=self.engine)
        self.session = scoped_session(session_factory)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def get_engine(cls):
        instance = cls.get_instance()
        return instance.engine

    @classmethod
    def get_session(cls):
        instance = cls.get_instance()
        return instance.session

    @staticmethod
    def close_current_session():
        """
        Cierra la sesión asociada al hilo actual.
        """
        DBConnection.get_session().remove()