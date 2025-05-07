import ast
import json
from abc import abstractmethod, ABC
from dataclasses import dataclass
from typing import List, Tuple, Any

import pydantic

from config import REPO_ROOT_ABSOLUTE_PATH, OFFICIAL_DOCS_RELATIVE_PATH, CODE_REPO_ROOT_ABSOLUTE_PATH, GITLAB_PROJECT_URL, GITLAB_API_URL, GITLAB_PROJECT_NORMAL_URL

from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.tools import BaseTool
import json


@dataclass
class Citation:
    doc_name: str
    doc_url: str
    doc_explanation: str

    # para serializaciones
    def __str__(self):
        return json.dumps({
            "type": "Citation",
            "data": {
                "doc_name": self.doc_name,
                "doc_url": self.doc_url,
                "doc_explanation": self.doc_explanation
            }
        })

    # para prints
    def to_string(self):
        return f"""Nombre de documento: {self.doc_name}
URL: {self.doc_url}
{self.doc_explanation}"""

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

    def to_dict(self):
        """Serializa el objeto CitedAIMessage a JSON"""
        try:
            citations_serialized = [citation.__str__() for citation in self.citations]
            return {
                "type": "CitedAIMessage",
                "data": {
                    "message_type": self.type,
                    "content": self.content,
                    "citations": citations_serialized
                }
            }
        except Exception as e:
            print(f"Error serializando CitedAIMessage: {e}")

    @staticmethod
    def from_string(string: str):
        """Reconstruye un objeto CitedAIMessage desde una cadena JSON"""
        try:
            json_data = json.loads(string)

            if json_data.get("type") != "CitedAIMessage":
                raise ValueError("El JSON no contiene un CitedAIMessage válido")

            data = json_data.get("data", {})
            content = data.get("content", "")
            citations_str = data.get("citations", [])

            # Reconstruir las citations
            citations = []
            for citation_str in citations_str:
                citation = Citation.from_string(citation_str)
                if citation:
                    citations.append(citation)

            # Crear un mensaje base para pasar al constructor
            base_message = AIMessage(content=content)

            return CitedAIMessage(
                message=base_message,
                citations=citations
            )
        except Exception as e:
            print(f"Error al deserializar CitedAIMessage: {e}")
            return None

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

class CodeResponseParser(ResponseParser):
    def parse_tool_response(self, response: str) -> dict:
        available_documents = {}
        try:
            file_list = ast.literal_eval(response)
            for doc in file_list:
                relative_path = doc
                available_documents[relative_path] = ""

            return available_documents
        except Exception as e:
            print(f"Error parseando respuesta de documentos del respositorio de código: {e}")
            return {}

class GitlabResponseParser(ResponseParser):
    def __init__(self, path_to_cut: str):
        super().__init__(
            path_to_cut=path_to_cut
        )

    def parse_tool_response(self, response: List[dict]) -> dict:
        available_documents = {}
        try:
            for elem in response:
                elem_url = elem.get("web_url")
                path_to_cut = self.kwargs.get("path_to_cut")
                if path_to_cut and elem_url.startswith(path_to_cut):
                    path = elem_url[len(path_to_cut):]
                    path = path.lstrip("/\\")
                else:
                    continue

                path_routes = path.split("/")

                doc_id = path_routes[-1]
                extra_path = ""
                for path_elem in path_routes[:-1]:
                    extra_path+=f"{path_elem}/"
                extra_path = extra_path.strip("/\\")

                available_documents[doc_id] = extra_path

        except Exception as e:
            print(f"Error parseando fuente de datos gitlab: {e}")

        finally:
            return available_documents





class DataSource(ABC):
    url: str
    get_documents_tool_name: str | List[str]
    # diccionario con el nombre del documento y prefijo necesario en la url -> algunas fuentes como Confluence requieren poner el id de la página además del nombre en la url
    available_documents: dict[str, str]
    # La id del DataSource para citar a la propia fuente de datos
    docs_id: str
    parser: ResponseParser

    def __init__(self, get_documents_tool_name: List[str], url: str, docs_id: str, use_example: str, response_parser: ResponseParser, tool_args: List[dict] = None):
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
        self.available_documents = {}
        try:
            for tool in agent_tools:
                if tool.name in self.get_documents_tool_name:
                    tool_index = self.get_documents_tool_name.index(tool.name)

                    get_documents_tool = tool

                    tool_response = await get_documents_tool.ainvoke(self.tool_args[tool_index])
                    self.available_documents.update(self.parser.parse_tool_response(tool_response))

            if self.available_documents == {}:
                raise Exception("No se ha encontrado la herramienta para listar los documentos")

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
            if doc_extra_url != "":
                doc_extra_url = f"/{doc_extra_url}"
            resource_url += f"{doc_extra_url}/{document_name}"
            
        return Citation(
            doc_name=document_name,
            doc_url=resource_url,
            doc_explanation=doc_explanation,
        )
            
class GoogleDriveDataSource(DataSource):
    def __init__(self, get_documents_tool_name: str):
        super().__init__(
            get_documents_tool_name=[get_documents_tool_name],
            tool_args=[{}],
            url="https://drive.google.com/drive/u/0/folders/1axp3gAWo6VeAFq16oj1B5Nm06us2FBdR",
            docs_id="google_drive_documents",
            use_example="if there is a file named file.html: doc_name = file.html",
            response_parser=GoogleDriveResponseParser()

        )
class FileSystemDataSource(DataSource):
    def __init__(self, get_documents_tool_name: str, tool_args: dict):
        super().__init__(
            get_documents_tool_name=[get_documents_tool_name],
            tool_args=[tool_args],
            url=f"file://{tool_args["path"]}",
            docs_id="oficial_documentation",
            use_example="if you want to reference the file file.md: doc_name=file.md",
            response_parser=FileSystemResponseParser(path_to_cut=tool_args["path"])
        )
class ConfluenceDataSource(DataSource):
    def __init__(self, get_documents_tool_name: str, tools_args: dict):
        super().__init__(
            get_documents_tool_name=[get_documents_tool_name],
            tool_args=[tools_args],
            url=f"https://martin-tfg.atlassian.net/wiki/spaces/~7120204ae5fbc225414096ab7a3348546ff647",
            docs_id="confluence_documentation",
            use_example="If you want to reference the page with title page_title: doc_name=page_title",
            response_parser=ConfluenceResponseParser()
        )
class GitLabDataSource(DataSource):
    def __init__(self, get_documents_tool_name: List[str], tool_args: List[dict]):
        super().__init__(
            get_documents_tool_name=get_documents_tool_name,
            tool_args=tool_args,
            url=GITLAB_PROJECT_NORMAL_URL,
            docs_id="gitlab_repository",
            use_example="If you want to cite a commit, use its id: doc_name=87bde70d722242000a8d997ed83cef6324bf19c6\nIf you want to cite an issue, use its iid: doc_name=3",
            response_parser=GitlabResponseParser(path_to_cut=GITLAB_PROJECT_NORMAL_URL)
        )
class CodeDataSource(DataSource):
    def __init__(self, get_documents_tool_name: str, tool_args: dict):
        super().__init__(
            get_documents_tool_name=[get_documents_tool_name],
            tool_args=[tool_args],
            url=f"file://{CODE_REPO_ROOT_ABSOLUTE_PATH}",
            docs_id="code_repository",
            use_example="If you want to cite the document notebook1.pynb: doc_name=notebooks/notebook1.pynb\nIf you want to cite the directory_1 directory: doc_name=relative/path/to/dir/directory_1",
            response_parser=CodeResponseParser()
        )









