from src.BaseAgent import AgentState
from src.planner_agent.models import PlannerResponse


"""
Dejar en fichero aparte para evitar importaciones circulares MainAgent-PlannerAgent
"""

class MainAgentState(AgentState):
    formatter_result: str
    planner_high_level_plan: PlannerResponse
    planner_current_step: int
    planner_scratchpad: str
