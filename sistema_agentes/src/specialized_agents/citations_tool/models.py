import json
from abc import abstractmethod, ABC
from dataclasses import dataclass
from typing import List, Tuple, Any
from config import REPO_ROOT_ABSOLUTE_PATH, OFICIAL_DOCS_RELATIVE_PATH, CODE_REPO_ROOT_ABSOLUTE_PATH

from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.tools import BaseTool


@dataclass
class Citation:
    doc_name: str
    doc_url: str
    doc_explanation: str

    def __str__(self):
        return json.dumps({
            "type": "Citation",
            "data": {
                "doc_name": self.doc_name,
                "doc_url": self.doc_url,
                "doc_explanation": self.doc_explanation
            }
        })

    @classmethod
    def from_string(cls, s):
        try:
            data = json.loads(s)
            if data.get("type") == "Citation":
                return cls(**data["data"])
        except Exception as e:
            pass

class CitedAIMessage(BaseMessage):
    citations: List[Citation]

    def __init__(self, message: BaseMessage, citations: List[Citation]):
        super().__init__(
            type="ai_cited",
            content=message.content,
            citations=citations
        )

    def format_to_ai_message(self) -> AIMessage:
        citations_str = "\n".join(citation.__str__() for citation in self.citations)
        return AIMessage(
            content=f"{self.content}\nCitations:\n{citations_str}"
        )


class ResponseParser(ABC):
    kwargs: dict
    def __init__(self, **kwargs):
        self.kwargs=kwargs

    def parse_tool_response(self, response: str) -> dict:
        """
        Parsea la respuesta de una tool al formato de citas esperado [nombre_fichero, prefijo_fichero]
        """

class GoogleDriveResponseParser(ResponseParser):
    def parse_tool_response(self, response: str) -> dict:
        tools_json = json.loads(response)
        tool_list = tools_json["documents"]

        available_documents = {}
        for document in tool_list:
            available_documents[document["name"]] = document["url"]

        return available_documents

class FileSystemResponseParser(ResponseParser):
    def __init__(self, path_to_cut: str):
        super().__init__(
            path_to_cut=path_to_cut
        )

    def parse_tool_response(self, response: str) -> dict:
        path_to_cut = self.kwargs.get("path_to_cut")
        file_paths = response.split("\n")
        available_documents = {}

        for file_path in file_paths:
            if path_to_cut and file_path.startswith(path_to_cut):
                relative_path = file_path[len(path_to_cut):]
                relative_path = relative_path.lstrip("/\\")
            else:
                relative_path = file_path

            available_documents[relative_path] = ""
        return available_documents

class ConfluenceResponseParser(ResponseParser):
    def __init__(self):
        super().__init__()

    def parse_tool_response(self, response: str) -> dict:
        available_documents = {}
        try:
            json_response = json.loads(response)
            for doc in json_response:
                id = doc.get("id")
                title = doc.get("title")
                type = doc.get("type")

                available_documents[title] = f"{type}s/{id}"

            return available_documents

        except Exception as e:
            print(f"Error parseando respuesta de documentos Confluence: {e}")
            return {}


class DataSource(ABC):
    url: str
    get_documents_tool_name: str
    # diccionario con el nombre del documento y prefijo necesario en la url -> algunas fuentes como Confluence requieren poner el id de la página además del nombre en la url
    available_documents: dict[str, str]
    # La id del DataSource para citar a la propia fuente de datos
    docs_id: str
    parser: ResponseParser

    def __init__(self, get_documents_tool_name: str, url: str, docs_id: str, use_example: str, response_parser: ResponseParser, tool_args: dict = None):
        if not tool_args:
            tool_args = {}

        self.get_documents_tool_name = get_documents_tool_name
        self.tool_args = tool_args
        self.url = url
        self.docs_id = docs_id
        self.use_example = use_example
        self.parser = response_parser

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

            tool_response = await get_documents_tool.ainvoke(self.tool_args)
            self.available_documents = self.parser.parse_tool_response(tool_response)

        except Exception as e:
            self.available_documents = {}
        
        finally:
            self.available_documents[self.docs_id] =  ""
        
    def resource_exists(self, document_name: str) -> bool:
        return document_name in self.available_documents

    def format_citation(self, document_name: str, doc_explanation: str) -> Citation:
        """Formatea una cita para un recurso específico"""
        resource_url = self.url
        if document_name != self.docs_id:
            doc_extra_url = self.available_documents[document_name]
            resource_url += f"/{doc_extra_url}/{document_name}"
            
        return Citation(
            doc_name=document_name,
            doc_url=resource_url,
            doc_explanation=doc_explanation,
        )
            
class GoogleDriveDataSource(DataSource):
    def __init__(self, get_documents_tool_name: str):
        super().__init__(
            get_documents_tool_name=get_documents_tool_name,
            tool_args={},
            url="https://drive.google.com/drive/u/0/folders/1axp3gAWo6VeAFq16oj1B5Nm06us2FBdR",
            docs_id="google_drive_documents",
            use_example="if there is a file named file.html: doc_name = file.html",
            response_parser=GoogleDriveResponseParser()

        )
class FileSystemDataSource(DataSource):
    def __init__(self, get_documents_tool_name: str, tool_args: dict):
        super().__init__(
            get_documents_tool_name=get_documents_tool_name,
            tool_args=tool_args,
            url=f"file://{tool_args["path"]}",
            docs_id="oficial_documentation",
            use_example="if you want to reference the file file.md: doc_name=file.md",
            response_parser=FileSystemResponseParser(path_to_cut=tool_args["path"])
        )
class ConfluenceDataSource(DataSource):
    def __init__(self, get_documents_tool_name: str, tools_args: dict):
        super().__init__(
            get_documents_tool_name=get_documents_tool_name,
            tool_args=tools_args,
            url=f"https://martin-tfg.atlassian.net/wiki/spaces/~7120204ae5fbc225414096ab7a3348546ff647",
            docs_id="confluence_documentation",
            use_example="If you want to reference the page with title page_title: doc_name=page_title",
            response_parser=ConfluenceResponseParser()
        )
class GitLabDataSource(DataSource):
    def __init__(self, get_documents_tool_name: str):
        super().__init__(
            get_documents_tool_name=get_documents_tool_name,
            url=f"https://gitlab.devops.lksnext.com/lks/genai/ia-core-tools",
            docs_id="gitlab_repository",
            use_example="",
            response_parser=None
        )
class CodeDataSource(DataSource):
    def __init__(self, get_documents_tool_name: str, tool_args: dict):
        super().__init__(
            get_documents_tool_name=get_documents_tool_name,
            tool_args=tool_args,
            url=f"{CODE_REPO_ROOT_ABSOLUTE_PATH}",
            docs_id="code_repository",
            use_example="",
            response_parser=None
        )









