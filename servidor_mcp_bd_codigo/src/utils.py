
def get_file_text(path: str) -> str:
    """
    Reads the content of a file and returns it as a string.

    Args:
        path (str): The path to the file.

    Returns:
        str: The content of the file.
    """
    with open(path, 'r', encoding='utf-8') as file:
        return file.read()