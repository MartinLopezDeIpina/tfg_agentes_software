from pathlib import Path
from typing import List, Union, Sequence, Tuple

from langchain_community.adapters.openai import convert_openai_messages
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, messages_from_dict
from langgraph.store.base import Item, SearchItem
from networkx.classes import is_empty
from rich.console import Console
from rich.markdown import Markdown

from src.specialized_agents.citations_tool.models import Citation


def tab_all_lines_x_times(text: str, times: int = 1) -> str:
    """
    Añade x tabulaciones a cada línea de un texto.
    """
    lines = text.splitlines()
    tabbed_lines = ["\t" * times + line for line in lines]
    return "\n".join(tabbed_lines)

def print_markdown(string: str):
    console = Console()
    md = Markdown(string)
    console.print(md)

def get_list_from_string_comma_separated_values(values_string: str):
    values_list = [element.strip() for element in values_string.split(',')]
    return values_list

def get_list_string_with_indexes(list: List[str]) -> str:
    string_result = ""
    for i, element in enumerate(list):
        string_result += f"{i}. {element}\n\n"

    return string_result

def read_file_content(file: Path) -> str:
    try:
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
        return content

    except Exception as e:
        print(f"Error leyendo fichero {file}")
        return ""
    
def get_memory_prompt_from_docs(memory_docs: List[SearchItem]) -> List[AIMessage]:
    """
    Devuelve la descripción de varios documentos extraídos de una colección de memoria
    """
    memories_list = []
    for i, memory in enumerate(memory_docs):
        cites = [Citation.from_string(citation) for citation in memory.value.get("cites")]
        cites_string = f"-Cited documents: {",".join([cite.doc_name for cite in cites])}"
        memory_string = f"Memory passage {i}: {memory.value.get("concept")}\n\t{cites_string}"
        memories_list.append(
            AIMessage(
                content=memory_string
            )
        )
    return memories_list

def _normalize_messages(input_dict: dict) -> list:
    messages = input_dict.get("messages", [])
    try:
        messages = convert_openai_messages(messages)
    except Exception as e:
        print("Error parsing messages from input dictionary, using empty list.")
        messages = []
    return messages

def normalize_agent_input_for_reasoner_agent(input_dict: dict) -> dict:
    query = input_dict.get("query", "")
    messages = _normalize_messages(input_dict)

    messages.append(HumanMessage(content=query))
    if len(messages) > 1:
        conversation_text = format_conversation_as_query(messages)
        input_dict["query"] = conversation_text

    input_dict["messages"] = messages
    return input_dict

def normalize_agent_input_for_orchestrator_agent(input_dict: dict) -> dict:
    messages = _normalize_messages(input_dict)
    input_dict["messages"] = messages
    return input_dict

def format_conversation_as_query(messages: List[BaseMessage]) -> str:
    """Convert conversation messages into a single descriptive query text for planner."""
    if not messages:
        return ""
    
    conversation_parts = []

    for msg in messages[:-1]:
        if isinstance(msg, HumanMessage):
            conversation_parts.append(f"User: {msg.content}")
        elif isinstance(msg, AIMessage):
            conversation_parts.append(f"Assistant: {msg.content}")

    context_summary = "Previous conversation context:\n" + "\n".join(conversation_parts)
    return f"{context_summary}\n\nCurrent user request: {messages[-1].content}"


def validate_messages_format(messages: List[dict]) -> tuple[bool, str]:
    """
    Validate the format of messages from frontend requests.
    
    Args:
        messages: List of message dictionaries with 'role' and 'content' keys
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not messages:
        return False, "No messages provided"
    
    for i, msg in enumerate(messages):
        if not isinstance(msg, dict):
            return False, f"Message {i} is not a dictionary"
        
        if 'role' not in msg:
            return False, f"Message {i} missing 'role' field"
        
        if 'content' not in msg:
            return False, f"Message {i} missing 'content' field"
        
        if not isinstance(msg['content'], str):
            return False, f"Message {i} 'content' must be a string"
        
        valid_roles = ['user', 'assistant', 'system']
        if msg['role'] not in valid_roles:
            return False, f"Message {i} has invalid role '{msg['role']}'. Must be one of: {valid_roles}"
    
    return True, ""


def calculate_token_usage(messages: List[dict], result) -> Tuple[int, int, int, str]:
    """
    Calculate token usage for OpenAI-compatible API response.
    Args:
        messages: List of input messages
        result: Agent result (can be CitedAIMessage or string)
    Returns:
        Tuple of (prompt_tokens, completion_tokens, total_tokens, result_content)
    """
    prompt_content = ' '.join([msg.get('content', '') for msg in messages])
    prompt_tokens = len(prompt_content.split())
    
    # Handle CitedAIMessage objects vs strings
    if hasattr(result, 'content'):
        completion_tokens = len(str(result.content).split())
        result_content = str(result.content)
    else:
        completion_tokens = len(str(result).split())
        result_content = str(result)
    
    total_tokens = prompt_tokens + completion_tokens
    return prompt_tokens, completion_tokens, total_tokens, result_content