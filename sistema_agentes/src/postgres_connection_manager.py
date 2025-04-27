import os

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
import asyncio
from psycopg_pool import AsyncConnectionPool
from src.globals import global_exit_stack

class PostgresPoolManager:
    """
    Patrón singleton con control de concurrencia.
    El cerrojo garantiza que nadie intente inicializarlo si ya está inicializado.
    https://langchain-ai.github.io/langgraph/how-tos/persistence_postgres/#use-async-connection

    Utiliza el contexto asíncrono global, no es necesario gestionar la limpieza
    """
    _instance = None
    _pool = None
    _checkpointer = None
    _initialized = False
    _lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls):
        """Obtener la instancia singleton del pool manager"""

        if cls._instance is None:
            cls._instance = cls()

        if not cls._initialized:
            async with cls._lock:
                if not cls._initialized:

                    db_user=os.getenv("DB_USER")
                    db_password=os.getenv("DB_PASSWORD")
                    db_host=os.getenv("DB_HOST")
                    db_port=os.getenv("DB_PORT")
                    db_name=os.getenv("DB_NAME")
                    connection_string = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
                    connection_kwargs = {
                        "autocommit": True,
                        "prepare_threshold": 0,
                    }

                    # Crear el pool con AsyncConnectionPool
                    pool_ctx = AsyncConnectionPool(
                        conninfo=connection_string,
                        max_size=10,
                        min_size=5,
                        kwargs=connection_kwargs
                    )

                    # Registramos el pool en el exit_stack global
                    cls._pool = await global_exit_stack.enter_async_context(pool_ctx)

                    # Crear el checkpointer usando el pool
                    cls._checkpointer = AsyncPostgresSaver(cls._pool)

                    # Configurar las tablas en PostgreSQL
                    await cls._checkpointer.setup()

                    cls._initialized = True
                    print(f"PostgreSQL pool inicializado")

        return cls._instance

    def get_checkpointer(self):
        """Obtener el checkpointer para usar en agentes"""
        if not self._initialized:
            raise RuntimeError("PostgresPoolManager no inicializado")
        return self._checkpointer