from utils.utils import tab_all_lines, apend_with_x_tab_to_text


def format_retrieved_chunks_into_string(response: dict[int, dict]) -> str:
    """
    Formatea los chunks recuperados en json a una cadena de texto con tabulaciones y saltos de línea para 
    que el LLM pueda entenderlo mejor.
    Formato de entrada por cada chunk:
            [chunk_id]:{
            "chunk_id": chunk_id,
            "chunk_content": chunk_content,
            "path": absolute path of the chunk's file,
            "referenced_chunks": list of chunks that reference this chunk
            "referencing chunks": list of chunks that are referenced by this chunk
        }
    """
    formatted_string = ""
    for chunk_id, chunk in response.items():
        chunk_str = ""
        chunk_str += f"->Chunk {chunk_id} in file {chunk["path"]}:\n"
        chunk_str = apend_with_x_tab_to_text(chunk_str, chunk["chunk_content"], 1)
        formatted_string += chunk_str
        if chunk['referenced_chunks'] != {}:
            formatted_string += "\nReferenced Chunks:\n"
            for ref_chunk_id, ref_chunk in chunk['referenced_chunks'].items():
                ref_chunk_string = "\n"
                ref_chunk_string += f"+Chunk {chunk_id} in file {ref_chunk["path"]}\n"
                ref_chunk_string = apend_with_x_tab_to_text(ref_chunk_string, ref_chunk["chunk_content"], 1)
                formatted_string = apend_with_x_tab_to_text(formatted_string, ref_chunk_string)
        if chunk['referencing_chunks'] != {}:
            formatted_string += "\nReferenced by chunks:\n"
            for ref_chunk_id, ref_chunk in chunk['referencing_chunks'].items():
                ref_chunk_string = "\n"
                ref_chunk_string += f"+Chunk {chunk_id} in file {ref_chunk["path"]}\n"
                ref_chunk_string = apend_with_x_tab_to_text(ref_chunk_string, ref_chunk["chunk_content"], 1)
                formatted_string = apend_with_x_tab_to_text(formatted_string, ref_chunk_string)
        formatted_string += "\n\n"

    return formatted_string
    
    
    