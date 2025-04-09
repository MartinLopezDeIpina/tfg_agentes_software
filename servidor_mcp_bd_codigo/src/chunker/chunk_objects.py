from dataclasses import dataclass
from tree_sitter import Point


@dataclass
class Definition:
    start_point: Point
    end_point: Point
    name: str
    is_class: bool
