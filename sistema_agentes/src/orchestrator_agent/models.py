from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

class AgentName(str, Enum):
    FILE_SYSTEM = "file_system_agent"
    GOOGLE_DRIVE = "google_drive_agent"
    GITLAB = "gitlab_agent"
    CONFLUENCE = "confluence_agent"
    CODE = "code_agent"

class AgentStep(BaseModel):
    agent_name: AgentName = Field(
        description="Name of the agent that will execute this step"
    )
    query: str = Field(
        description="Query or instruction that will be sent to the agent"
    )

    def to_string(self):
        return f"{self.agent_name}: {self.query}"

class OrchestratorPlan(BaseModel):
    steps_to_complete: List[AgentStep] = Field(
        description="List of steps that should be completed in parallel. Each step will be an agent call."
    )

    def to_string(self) -> str:
        return "-\n".join([step.to_string() for step in self.steps_to_complete])