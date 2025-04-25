from typing import List, Tuple

from pydantic import BaseModel, Field

class CiteReference(BaseModel):
    cite_id: int = Field(description="Citation ID")
    cited_document_name: str = Field(description="Name of the cited document")

class FormatterResponse(BaseModel):
    response: str = Field(description="Markdown response for the user query. Should NOT contain references or URLs.")
    citations: List[CiteReference] = Field(description="List of the available citations to reference")