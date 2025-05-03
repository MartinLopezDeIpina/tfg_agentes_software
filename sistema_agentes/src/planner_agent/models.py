from abc import abstractmethod
from typing import List, Any

from langchain_core.messages import BaseMessage, AIMessage
from pydantic import BaseModel, Field

from src.orchestrator_agent.models import AgentStep, OrchestratorPlan
from src.utils import tab_all_lines_x_times

class PlannerResponse(BaseModel):
    plan_reasoning: str = Field(description="The logical explanation of why this execution plan was chosen")
    steps: List[Any] = None
    finished: bool = Field(description="Whether the plan is finished or not")

    def to_string(self) -> str:
        string = ""
        string += f"Planning reasoning:\n{tab_all_lines_x_times(self.plan_reasoning)}\n"
        steps_str = self._steps_to_string()
        string += f"Plan steps:\n{steps_str}\n"
        string += f"Finshed plan:{self.finished}"
        return string

    @abstractmethod
    def _steps_to_string(self) -> str:
        """
        Define la lógica de convertir los steps a strings
        """

class BasicPlannerResponse(PlannerResponse):
    steps: List[str] = Field(description="The list of steps remaining to execute on the plan")

    def _steps_to_string(self) -> str:
        if self.steps:
            return "\n".join(self.steps)
        return ""

class OrchestratorPlannerResponse(PlannerResponse):
    steps: List[OrchestratorPlan] = Field(description="The list of steps remaining to execute on the plan. Each step is a plan to execute one or more agents.")

    def _steps_to_string(self) -> str:
        steps_string = ""
        if self.steps:
            for i, step in enumerate(self.steps):
                steps_string += f"Step {i}: {tab_all_lines_x_times(step.to_string())}\n"
        return steps_string

class PlanAIMessage(BaseMessage):
    def __init__(self, message: BaseMessage):
        super().__init__(
            type="ai_plan",
            content=message.content,
        )

    def format_to_ai_message(self) -> AIMessage:
        return AIMessage(
            content=f"{self.content}"
        )
