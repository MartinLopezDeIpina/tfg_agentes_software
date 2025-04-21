from langchain_core.tools import tool, BaseTool
from typing import Callable, Any, Dict, Optional, List, Union

from src.mcp_client.tool_wrapper import patch_tool_with_exception_handling
from src.specialized_agents.citations_tool.models import DataSource, Citation


def create_citation_tool(data_sources: List[DataSource]) -> BaseTool:
    """
    Factory function para crear la tool de citación que puede utilizar múltiples fuentes de datos.
    El agente no debe preocuparse por las fuentes de datos, estas están configuradas.

    Args:
        data_sources: Lista de fuentes de datos disponibles para la herramienta

    Returns:
        Una herramienta de LangChain configurada
    """

    base_docstring = """
        Cite a specific document from one or more data sources.
        Args:
            doc_name: The identifier of the document to cite.
            explanation: Explanation of why this document is being cited, referencing the section of the document used.
        Returns:
            Confirmation of the citation or error message if not found
            
        If you want to cite the data source, use doc_name = {source_doc_name}
            
        Usage example:
        {tool_use_example}
    """
    source_doc_name = " ".join(data_source.docs_id for data_source in data_sources)
    tool_use_example = "\n".join(data_source.use_example for data_source in data_sources)

    docstring = base_docstring.format(
        source_doc_name=source_doc_name,
        tool_use_example=tool_use_example,
    )

    async def cite_document(doc_name: str, explanation: str) -> Citation or str:
        """
        Utilizar doc_string dinámico en función de qué fuente de datos se utilice para ajustar la tool a su agente.
        """
        # Si no hay fuentes de datos configuradas
        if not data_sources:
            return "No hay fuentes de datos configuradas para citar documentos."

        # Buscar la fuente de datos por nombre
        for source in data_sources:
            # Verificar si el recurso existe en esta fuente
            exists = source.resource_exists(doc_name)
            if exists:
                return source.format_citation(doc_name, explanation)

        return f"No se encontró '{doc_name}' en las fuentes de datos disponibles"

    cite_document.__doc__ = docstring
    # decorar con tool después de haber cambiado el docstring
    cite_document = tool(cite_document)

    return patch_tool_with_exception_handling(cite_document)