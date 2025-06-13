"""
Model configurations for the agent system.
Maps OpenWebGUI model names to agent configurations.
"""
from dataclasses import dataclass
from src.main_agent.main_agent_builder import MainAgentType, PlannerAgentType, OrchestratorAgentType


@dataclass
class AgentConfiguration:
    """Configuration for an agent model"""
    main_type: MainAgentType
    planner_type: PlannerAgentType
    orchestrator_type: OrchestratorAgentType
    use_double_agent: bool = False


class ModelConfigs:
    """Container for all model configurations"""
    
    PLANIFICADOR_UNIFICADO = AgentConfiguration(
        main_type=MainAgentType.BASIC,
        planner_type=PlannerAgentType.ORCHESTRATOR_PLANNER,
        orchestrator_type=OrchestratorAgentType.DUMMY
    )
    
    AGENTE_SIMPLE = AgentConfiguration(
        main_type=MainAgentType.ORCHESTRATOR_ONLY,
        planner_type=PlannerAgentType.NONE,
        orchestrator_type=OrchestratorAgentType.REACT
    )
    
    AGENTE_DOBLE = AgentConfiguration(
        # Dummy values since use_double_agent=True
        main_type=MainAgentType.BASIC,
        planner_type=PlannerAgentType.BASIC,
        orchestrator_type=OrchestratorAgentType.BASIC,

        use_double_agent=True
    )

    AGENTE_DUMMY = AgentConfiguration(
        main_type=None,
        planner_type=None,
        orchestrator_type=None,
    )
    
    _CONFIGS = {
        "planificador_unificado": PLANIFICADOR_UNIFICADO,
        "agente_simple": AGENTE_SIMPLE,
        "agente_doble": AGENTE_DOBLE,
        "agente_dummy": AGENTE_DUMMY
    }
    
    DEFAULT_MODEL = "planificador_unificado"
    
    @classmethod
    def get_configuration(cls, model: str = None) -> AgentConfiguration:
        """Get the configuration for a given model name"""
        if model is None or model not in cls._CONFIGS:
            model = cls.DEFAULT_MODEL
        return cls._CONFIGS[model]


def get_model_configuration(model: str = None) -> AgentConfiguration:
    """
    Get the configuration for a given model name
    """
    return ModelConfigs.get_configuration(model)

def get_available_models():
    """
    Get list of available model configurations for OpenWebGUI
    """
    return [
        {
            "id": "agente_dummy",
            "object": "model",
            "created": 1677652288,
            "owned_by": "sistema-agentes",
            "description": "Agente dummy sin funcionalidades"
        },
        {
            "id": "planificador_unificado",
            "object": "model",
            "created": 1677652288,
            "owned_by": "sistema-agentes",
            "description": "Agente completo con planificador unificado y todos los MCP servers"
        },
        {
            "id": "agente_simple",
            "object": "model",
            "created": 1677652288,
            "owned_by": "sistema-agentes",
            "description": "Agente simple con funcionalidades básicas y patrón ReAct"
        },
        {
            "id": "agente_doble",
            "object": "model",
            "created": 1677652288,
            "owned_by": "sistema-agentes",
            "description": "Agente inteligente que clasifica consultas y usa el agente apropiado"
        }
    ]