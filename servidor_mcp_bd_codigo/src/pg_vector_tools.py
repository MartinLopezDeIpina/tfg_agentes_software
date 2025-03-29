from langchain_huggingface import HuggingFaceEmbeddings
from langchain_postgres.vectorstores import PGVector

from src.db.db_connection import DBConnection

class PGVectorTools:
    def __init__(self):
        """Initializes the PGVectorTools with a SQLAlchemy engine."""
        self.db = DBConnection.get_instance()
        #self.Session = self.db.session

    def search_similar_resources(self, query, max_results=5):
        """Searches for similar resources in the pgvector table using langchain vector store."""
        vector_store = PGVector(
            embeddings=HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2"),
            collection_name="stackoverflow",
            connection=self.db.engine,
            use_jsonb=True,
        )
        results = vector_store.similarity_search(
            query=query,
            k=max_results
        )
        return results

