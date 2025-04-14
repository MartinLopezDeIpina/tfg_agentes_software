from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

#todo: añadir opción de enumerado dinámico en tiempo de ejecución para activar/desactivar agentes

class AgentName(str, Enum):
    FILE_SYSTEM = "file_system_agent"
    GOOGLE_DRIVE = "google_drive_agent"
    GITLAB = "gitlab_agent"

class AgentStep(BaseModel):
    agent_name: AgentName = Field(
        description="Name of the agent that will execute this step"
    )
    query: str = Field(
        description="Query or instruction that will be sent to the agent"
    )

class OrchestratorPlan(BaseModel):
    steps_to_complete: List[AgentStep] = Field(
        description="List of steps that should be completed in parallel. Each step will be an agent call."
    )