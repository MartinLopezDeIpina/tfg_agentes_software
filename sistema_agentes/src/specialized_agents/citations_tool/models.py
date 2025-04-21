import json
from abc import abstractmethod, ABC
from dataclasses import dataclass
from typing import List, Tuple
from config import REPO_ROOT_ABSOLUTE_PATH, OFICIAL_DOCS_RELATIVE_PATH, CODE_REPO_ROOT_ABSOLUTE_PATH

from langchain_core.messages import AIMessage
from langchain_core.tools import BaseTool


@dataclass
class Citation:
    doc_name: str
    doc_url: str
    doc_explanation: str

class CitedAIMessage(AIMessage):
    citations: List[Citation]

    def __init__(self, message: AIMessage, citations: List[Citation]):
        super().__init__(content=message.content)

        self.citations = citations


class DataSource(ABC):
    url: str
    get_documents_tool_name: str
    # diccionario con el nombre del documento y prefijo necesario en la url -> algunas fuentes como Confluence requieren poner el id de la página además del nombre en la url
    available_documents: dict[str, str]
    # La id del DataSource para citar a la propia fuente de datos
    docs_id: str

    def __init__(self, get_documents_tool_name: str, url: str, docs_id: str):
        self.get_documents_tool_name = get_documents_tool_name
        self.url = url
        self.docs_id = docs_id
        self.set_available_documents()

    async def set_available_documents(self, agent_tools: List[BaseTool]) -> None:
        """
        Establece la lista de documentos disponibles en esta fuente de datos
        Busca entre las tools del agente la tool necesaria para listar los documentos disponibles
        """
        try:
            get_documents_tool = None
            for tool in agent_tools:
                if tool.name == self.get_documents_tool_name:
                    get_documents_tool = tool
            if not get_documents_tool:
                raise Exception("No se ha encontrado la herramienta para listar los documentos")

            tool_response = await get_documents_tool.ainvoke({})
            tools_str = tool_response.content[0].text
            tools_json = json.loads(tools_str)
            tool_list = tools_json["documents"]

            self.available_documents = {}
            for document in tool_list:
                self.available_documents[document["name"]] = document["url"]

        except Exception as e:
            self.available_documents = {}
        
        finally:
            self.available_documents[self.docs_id] =  ""
        
    async def resource_exists(self, document_name: str) -> bool:
        return document_name in self.available_documents

    def format_citation(self, document_name: str, doc_explanation: str) -> Citation:
        """Formatea una cita para un recurso específico"""
        resource_url = self.url
        if document_name != self.docs_id:
            doc_extra_url = self.available_documents[document_name]
            resource_url += f"/{doc_extra_url}{document_name}"
            
        return Citation(
            doc_name=document_name,
            doc_url=resource_url,
            doc_explanation=doc_explanation,
        )
            
class GoogleDriveDataSource(DataSource):
    def __init__(self, get_documents_tool_name: str):
        super().__init__(
            get_documents_tool_name=get_documents_tool_name,
            url="https://drive.google.com/drive/u/0/folders/1axp3gAWo6VeAFq16oj1B5Nm06us2FBdR",
            docs_id="google_drive_documents"
        )
class FileSystemDataSource(DataSource):
    def __init__(self, get_documents_tool_name: str):
        super().__init__(
            get_documents_tool_name=get_documents_tool_name,
            url=f"file://{REPO_ROOT_ABSOLUTE_PATH}/{OFICIAL_DOCS_RELATIVE_PATH}",
            docs_id="oficial_documentation"
        )
class ConfluenceDataSource(DataSource):
    def __init__(self, get_documents_tool_name: str):
        super().__init__(
            get_documents_tool_name=get_documents_tool_name,
            url=f"https://martin-tfg.atlassian.net/wiki/spaces/~7120204ae5fbc225414096ab7a3348546ff647/",
            docs_id="oficial_documentation"
        )
class GitLabDataSource(DataSource):
    def __init__(self, get_documents_tool_name: str):
        super().__init__(
            get_documents_tool_name=get_documents_tool_name,
            url=f"https://gitlab.devops.lksnext.com/lks/genai/ia-core-tools",
            docs_id="gitlab_repository"
        )
class CodeDataSource(DataSource):
    def __init__(self, get_documents_tool_name: str):
        super().__init__(
            get_documents_tool_name=get_documents_tool_name,
            url=f"{CODE_REPO_ROOT_ABSOLUTE_PATH}",
            docs_id="code_repository"
        )





