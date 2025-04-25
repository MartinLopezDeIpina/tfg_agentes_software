from pydantic import Field
from typing import List, Tuple

from pydantic import BaseModel


class Correction(BaseModel):
    concept: str = Field(description="Concept of the ground truth")
    included_cite: str or None = Field(description="Cite of the phrase that included the concept, None if it was not included")
    is_included: bool = Field(description="Whether the ground truth concept is included in the generated solution")

class JudgeLLMResponse(BaseModel):
    corrections: List[Correction] = Field(
        description="A list of corrections that determines whether each concept is included in the generated response"
    )
    tried_to_respond: bool = Field(description="Whether the question was actually responded or it was stated that not enough information is provided")