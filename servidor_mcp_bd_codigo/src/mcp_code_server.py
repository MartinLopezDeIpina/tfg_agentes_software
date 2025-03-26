from mcp.server.fastmcp import FastMCP

from src.pg_vector_tools import PGVectorTools

mcp = FastMCP("postgre")
pgvector_tools = PGVectorTools()

def get_prueba_base_datos():
    return "query base de datos"


@mcp.tool()
async def rag_code(query: str):
    """Get relevant documents from the code database for the given  query.

    Args:
        query (str): The query to search for.
    """
    similar_resources = pgvector_tools.search_similar_resources(query, 5)

    return similar_resources

if __name__ == "__main__":

    mcp.run(transport='sse')





