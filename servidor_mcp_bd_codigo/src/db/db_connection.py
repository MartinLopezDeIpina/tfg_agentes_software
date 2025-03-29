from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

class DBConnection:
    _instance = None

    DB_USER='postgres'
    DB_PASSWORD='c09f61d6f'
    DB_HOST='localhost'
    DB_PORT='5432'
    DB_NAME='postgres'


    """
    Devuelve una instancia del patrón Singleton para la conexión a la base de datos.
    
    Es un scoped session, se gestionan las sesiones internamente. 
    Uso: 
        session = DBConnection.get_instance()
        session.query(....)
    """
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            engine = create_engine(
               f"postgresql+psycopg2://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}",
                pool_size=5,
            )
            # Con el session factory y scoped session se supone que se maneja la concurrencia
            session_factory = sessionmaker(bind=engine)

            cls._instance = scoped_session(session_factory)

        """
            cls._instance = engine
        return cls._instance
        """
        return cls._instance
