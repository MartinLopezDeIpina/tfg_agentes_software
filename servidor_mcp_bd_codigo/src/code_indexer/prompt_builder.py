from dataclasses import dataclass
from typing import List, Tuple
from langchain_core.prompts import PromptTemplate
from src.code_indexer.prompts import system_prompt, user_prompt, prompt_parts_explanation
from utils.utils import get_start_to_end_lines_from_text_code, tab_all_lines
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage


@dataclass
class DocPromptPart:
    prompt_explanation: str
    prompt_part: str

class DocPromptBuilder:
    prompt_parts: List[DocPromptPart]
    system_prompt: str
    user_prompt_template: PromptTemplate
    prompt_parts_explanation: dict
    max_reference_chunks: int = 10
    max_file_extra_lines: int = 300

    def __init__(self, max_reference_chunks: int = 10, max_file_extra_lines: int = 300):
        self.max_reference_chunks = max_reference_chunks
        self.max_file_extra_lines = max_file_extra_lines

        self.system_prompt = system_prompt
        self.user_prompt_template = PromptTemplate(
            input_variables=["input_resources"],
            template=user_prompt
        )
        self.prompt_parts = []
        self.prompt_parts_explanation = prompt_parts_explanation

    def restart_prompt(self):
        self.prompt_parts = []

    def add_prompt_chunk_code(self, chunk_code: str, file_path: str):
        prompt_explanation = f"{self.prompt_parts_explanation["chunk_code"]} for file {file_path}"
        self.prompt_parts.append(DocPromptPart(prompt_explanation, chunk_code))

    def add_prompt_file_code(self, file_code: str, is_only_chunk_in_file: bool, chunk_start_line: int, chunk_end_line: int):
        """
        Si es el único chunk en el fichero, no hace falta añadir el código del fichero.
        """
        if not is_only_chunk_in_file:
            max_lines_top_bottom = self.max_file_extra_lines // 2
            start_line = max(0, chunk_start_line - max_lines_top_bottom)
            end_line = min(chunk_end_line + max_lines_top_bottom, len(file_code.splitlines()) - 1)
            cut_file_code = get_start_to_end_lines_from_text_code(file_code, start_line, end_line)

            self.prompt_parts.append(DocPromptPart(self.prompt_parts_explanation["file_code"], cut_file_code))

    def add_prompt_extra_docs(self, extra_docs: str):
        if extra_docs != "":
            self.prompt_parts.append(DocPromptPart(self.prompt_parts_explanation["extra_docs"], extra_docs))

    def add_prompt_repo_map(self, repo_map: str):
        self.prompt_parts.append(DocPromptPart(self.prompt_parts_explanation["repo_map"], repo_map))

    def add_prompt_referenced_chunks(self, referenced_chunks: List[Tuple[str, str]]):
        if len(referenced_chunks) > 0:
            referenced_chunks_str = ""

            for chunk in referenced_chunks:
                tabed_chunk = tab_all_lines(chunk[1])
                referenced_chunks_str += f"\n-Referenced chunk in file {chunk[0]}:\n{tabed_chunk}\n"

            self.prompt_parts.append(DocPromptPart(self.prompt_parts_explanation["referenced_chunks"], referenced_chunks_str))

    def add_prompt_referencing_chunks(self, referencing_chunks: List[Tuple[str, str]]):
        if len(referencing_chunks) > 0:
            referencing_chunks_str = ""

            for chunk in referencing_chunks:
                referencing_chunks_str += f"{self.prompt_parts_explanation["referencing_chunk_path"]}: {chunk[0]}\n{chunk[1]}\n"

            self.prompt_parts.append(DocPromptPart(self.prompt_parts_explanation["referencing_chunks"], referencing_chunks_str))

    def build_prompt(self) -> List[BaseMessage]:
        """
        Construye el prompt a partir de las partes añadidas.
        """
        prompt_resources = ""
        for i, part in enumerate(self.prompt_parts):
            tabed_prompt_part = tab_all_lines(part.prompt_part)
            prompt_resources += f"{i+1}. {part.prompt_explanation}:\n{tabed_prompt_part}\n\n"

        user_prompt = self.user_prompt_template.format(input_resources=prompt_resources)
        prompt = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_prompt)
        ]

        return prompt
