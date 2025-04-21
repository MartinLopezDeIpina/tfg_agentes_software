from langchain_core.tools import tool, BaseTool
from typing import Callable, Any, Dict, Optional, List, Union

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

    @tool
    async def cite_document(doc_id: str, explanation: str) -> Citation or str:
        """
        Cita un documento específico de una o más fuentes de datos.

        Args:
            doc_id: El identificador del documento a citar
            explanation: Explicación de por qué se cita este documento
        Returns:
            Confirmación de la cita o mensaje de error si no se encuentra
        """
        # Si no hay fuentes de datos configuradas
        if not data_sources:
            return "No hay fuentes de datos configuradas para citar documentos."

        # Buscar la fuente de datos por nombre
        for source in data_sources:
            # Verificar si el recurso existe en esta fuente
            exists = source.resource_exists(doc_id)
            if exists:
                return source.format_citation(doc_id, explanation)

        return f"No se encontró '{doc_id}' en las fuentes de datos disponibles"

    return cite_document