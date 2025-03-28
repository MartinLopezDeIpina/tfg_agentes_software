from grep_ast.tsl import get_language, get_parser  # noqa: E402
from grep_ast import filename_to_lang
from importlib import resources

from src.utils import get_file_text

def pruebas_repo_map():
    FILE_NAME = "/home/martin/open_source/ia-core-tools/app/tools/pgVectorTools.py"

    language = filename_to_lang(FILE_NAME)
    if not language:
        print(f"error, could not determine language for {FILE_NAME}")

    lang = get_language(language)
    parser = get_parser(language)

    # esto se puede poner en forma de paquete con __package__
    scm_file = resources.files(__package__).joinpath(
        "language_queries",
        f"{language}-tags.scm"
    )
    if not scm_file.exists():
        print(f"error, could not find {language}-tags.scm in package resources")

    query_scm = scm_file.read_text()

    code = get_file_text(FILE_NAME)
    if not code:
        print(f"error, could not read file {FILE_NAME}")
    tree = parser.parse(bytes(code, "utf-8"))

    # Run the tags queries
    query = lang.query(query_scm)
    captures = query.captures(tree.root_node)

    saw = set()

    all_nodes = []
    for tag, nodes in captures.items():
        all_nodes += [(node, tag) for node in nodes]

    for node, tag in all_nodes:
        if tag.startswith("name.definition."):
            kind = "def"
        elif tag.startswith("name.reference."):
            kind = "ref"
        else:
            continue

        saw.add(kind)

        print(f"node: {node}, tag: {tag}, kind: {kind}, text: {node.text.decode('utf-8')}")

