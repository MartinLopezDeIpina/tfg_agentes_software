from typing import List

from src.BaseAgent import AgentState
from src.planner_agent.models import PlannerResponse
from src.specialized_agents.citations_tool.models import Citation, CitedAIMessage

"""
Dejar en fichero aparte para evitar importaciones circulares MainAgent-PlannerAgent
"""

class MainAgentState(AgentState):
    formatter_result: CitedAIMessage
    planner_high_level_plan: PlannerResponse
    planner_current_step: int
    planner_scratchpad: str
