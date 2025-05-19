from typing import Literal
from pydantic import BaseModel

class ClassifierResponse(BaseModel):
    difficulty: Literal["EASY", "HARD"]