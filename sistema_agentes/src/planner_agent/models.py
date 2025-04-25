from typing import List

from pydantic import BaseModel, Field

from src.utils import tab_all_lines_x_times


class PlannerResponse(BaseModel):
    plan_reasoning: str = Field(description="The logical explanation of why this execution plan was chosen")
    steps: List[str] = Field(description="The list of steps remaining to execute on the plan")
    finished: bool = Field(description="Whether the plan is finished or not")
    
    def to_string(self) -> str:
        string = ""
        string += f"Planning reasoning:\n{tab_all_lines_x_times(self.plan_reasoning)}\n"
        string += f"Plan steps:\n{tab_all_lines_x_times("\n".join(self.steps))}\n"
        string += f"Finshed plan:{self.finished}"

        return string

        

