from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import List, Optional, Dict, Set, Tuple, Callable
from src.formatter_agent.formatter_graph import FormatterAgent
from src.main_agent.main_graph import MainAgent, BasicMainAgent, OrchestratorOnlyMainAgent
from src.orchestrator_agent.orchestrator_agent_graph import OrchestratorAgent, BasicOrchestratorAgent, \
    DummyOrchestratorAgent, ReactOrchestratorAgent
from src.planner_agent.planner_agent_graph import PlannerAgent, BasicPlannerAgent, OrchestratorPlannerAgent
from src.specialized_agents.SpecializedAgent import SpecializedAgent
from src.specialized_agents.code_agent.code_agent_graph import CodeAgent
from src.specialized_agents.confluence_agent.confluence_agent_graph import ConfluenceAgent, CachedConfluenceAgent
from src.specialized_agents.filesystem_agent.filesystem_agent_graph import FileSystemAgent
from src.specialized_agents.gitlab_agent.gitlab_agent_graph import GitlabAgent
from src.specialized_agents.google_drive_agent.google_drive_agent_graph import GoogleDriveAgent

class MainAgentType(Enum):
    BASIC = "basic"
    ORCHESTRATOR_ONLY = "orchestrator_only"

class PlannerAgentType(Enum):
    NONE = "none"
    BASIC = "basic"
    ORCHESTRATOR_PLANNER = "orchestrator_planner"

class OrchestratorAgentType(Enum):
    BASIC = "basic"
    DUMMY = "dummy"
    REACT = "react"

class IncompatibilityRule:
    """Define una regla de incompatibilidad entre agentes"""

    def __init__(self, check_func: Callable[[MainAgentType, PlannerAgentType, OrchestratorAgentType], bool],
                 error_message: str):
        """
        Inicializa una regla de incompatibilidad
        """
        self.check_func = check_func
        self.error_message = error_message

    def is_violated(self, main_type: MainAgentType, planner_type: PlannerAgentType,
                    orchestrator_type: OrchestratorAgentType) -> bool:
        """Verifica si la configuración viola esta regla"""
        return self.check_func(main_type, planner_type, orchestrator_type)


class AgentCompatibilityValidator:
    """Clase para validar la compatibilidad entre los diferentes tipos de agentes"""

    INCOMPATIBILITY_RULES = [
        #OrchestratorOnlyMainAgent no puede tener planificador
        IncompatibilityRule(
            lambda main, planner, orch: main == MainAgentType.ORCHESTRATOR_ONLY and planner != PlannerAgentType.NONE,
            "OrchestratorOnlyMainAgent no puede tener un planificador, debe usar PlannerAgentType.NONE"
        ),

        #BasicMainAgent requiere un planificador
        IncompatibilityRule(
            lambda main, planner, orch: main == MainAgentType.BASIC and planner == PlannerAgentType.NONE,
            "BasicMainAgent requiere un planificador, no puede usar PlannerAgentType.NONE"
        ),

        #OrchestratorPlannerAgent solo puede ir con DummyOrchestratorAgent
        IncompatibilityRule(
            lambda main, planner,
                   orch: planner == PlannerAgentType.ORCHESTRATOR_PLANNER and orch != OrchestratorAgentType.DUMMY,
            "OrchestratorPlannerAgent solo puede combinarse con DummyOrchestratorAgent"
        ),

        #DummyOrchestratorAgent solo puede ir con OrchestratorPlannerAgent
        IncompatibilityRule(
            lambda main, planner,
                   orch: orch == OrchestratorAgentType.DUMMY and planner != PlannerAgentType.ORCHESTRATOR_PLANNER,
            "DummyOrchestratorAgent solo puede combinarse con OrchestratorPlannerAgent"
        )
    ]

    @staticmethod
    def validate_configuration(main_type: MainAgentType, planner_type: PlannerAgentType,
                               orchestrator_type: OrchestratorAgentType) -> Tuple[bool, str]:
        """
        Valida si la configuración cumple con todas las reglas de compatibilidad

        Returns:
            Tuple[bool, str]: (es_valida, mensaje_error)
        """
        for rule in AgentCompatibilityValidator.INCOMPATIBILITY_RULES:
            if rule.is_violated(main_type, planner_type, orchestrator_type):
                return False, rule.error_message

        return True, ""


class FlexibleAgentBuilder:
    """Builder que permite cualquier combinación que no viole las reglas de incompatibilidad"""

    def __init__(self):
        self.reset()

    def reset(self) -> 'FlexibleAgentBuilder':
        """Reinicia el builder a sus valores por defecto"""
        self._specialized_agents: List[SpecializedAgent] = []
        self._available_agents: List[SpecializedAgent] = []
        self._main_agent_type: MainAgentType = MainAgentType.BASIC
        self._planner_type: PlannerAgentType = PlannerAgentType.BASIC
        self._orchestrator_type: OrchestratorAgentType = OrchestratorAgentType.BASIC
        self._formatter_agent: Optional[FormatterAgent] = None
        self._planner_agent: Optional[PlannerAgent] = None
        self._orchestrator_agent: Optional[OrchestratorAgent] = None
        return self

    def with_main_agent_type(self, main_agent_type: str) -> 'FlexibleAgentBuilder':
        """Establece el tipo de agente principal"""
        try:
            self._main_agent_type = MainAgentType(main_agent_type)
            return self
        except ValueError:
            valid_types = ", ".join([t.value for t in MainAgentType])
            raise ValueError(f"Tipo de agente principal no válido: {main_agent_type}. Opciones válidas: {valid_types}")

    def with_planner_type(self, planner_type: str) -> 'FlexibleAgentBuilder':
        """Establece el tipo de agente planificador"""
        try:
            self._planner_type = PlannerAgentType(planner_type)
            return self
        except ValueError:
            valid_types = ", ".join([t.value for t in PlannerAgentType])
            raise ValueError(f"Tipo de planificador no válido: {planner_type}. Opciones válidas: {valid_types}")

    def with_orchestrator_type(self, orchestrator_type: str) -> 'FlexibleAgentBuilder':
        """Establece el tipo de agente orquestador"""
        try:
            self._orchestrator_type = OrchestratorAgentType(orchestrator_type)
            return self
        except ValueError:
            valid_types = ", ".join([t.value for t in OrchestratorAgentType])
            raise ValueError(f"Tipo de orquestador no válido: {orchestrator_type}. Opciones válidas: {valid_types}")

    def with_specialized_agents(self, agents: List[SpecializedAgent] = None) -> 'FlexibleAgentBuilder':
        """Añade agentes especializados, o usa una configuración por defecto si no se especifican"""
        if agents is None:
            self._specialized_agents = [
                GoogleDriveAgent(),
                FileSystemAgent(),
                GitlabAgent(),
                CachedConfluenceAgent(),
                CodeAgent()
            ]
        else:
            self._specialized_agents = agents
        return self

    def with_formatter_agent(self, formatter_agent: FormatterAgent = None) -> 'FlexibleAgentBuilder':
        """Establece el agente formateador"""
        self._formatter_agent = formatter_agent if formatter_agent else FormatterAgent()
        return self

    async def initialize_agents(self) -> 'FlexibleAgentBuilder':
        """Inicializa los agentes especializados y crea las instancias de planner y orchestrator"""
        # Inicializar agentes especializados
        self._available_agents = []
        for agent in self._specialized_agents:
            try:
                await agent.init_agent()
                self._available_agents.append(agent)
            except Exception as e:
                print(f"Error conectando agente {agent.name}: {e}")

        # Crear el agente formateador si no existe
        if not self._formatter_agent:
            self._formatter_agent = FormatterAgent()

        # Crear el planificador según el tipo seleccionado
        if self._planner_type == PlannerAgentType.BASIC:
            self._planner_agent = BasicPlannerAgent(max_steps=2)
        elif self._planner_type == PlannerAgentType.ORCHESTRATOR_PLANNER:
            self._planner_agent = OrchestratorPlannerAgent(available_agents=self._available_agents)
        else:  # NONE
            self._planner_agent = None

        # Crear el orquestador según el tipo seleccionado
        if self._orchestrator_type == OrchestratorAgentType.BASIC:
            self._orchestrator_agent = BasicOrchestratorAgent(available_agents=self._available_agents)
        elif self._orchestrator_type == OrchestratorAgentType.DUMMY:
            self._orchestrator_agent = DummyOrchestratorAgent(available_agents=self._available_agents)
        elif self._orchestrator_type == OrchestratorAgentType.REACT:
            self._orchestrator_agent = ReactOrchestratorAgent(available_agents=self._available_agents, max_steps=2)
            await self._orchestrator_agent.init_agent()

        return self

    def validate(self) -> bool:
        """Valida que la configuración actual no viole ninguna regla de incompatibilidad"""
        is_valid, error_message = AgentCompatibilityValidator.validate_configuration(
            self._main_agent_type,
            self._planner_type,
            self._orchestrator_type
        )

        if not is_valid:
            raise ValueError(f"Configuración inválida: {error_message}")

        return True

    def build(self) -> MainAgent:
        """Construye y devuelve la instancia del agente principal validando la compatibilidad"""
        self.validate()

        if not self._formatter_agent:
            self._formatter_agent = FormatterAgent()

        # Construir el tipo de agente principal adecuado
        if self._main_agent_type == MainAgentType.BASIC:
            return BasicMainAgent(
                planner_agent=self._planner_agent,
                orchestrator_agent=self._orchestrator_agent,
                formatter_agent=self._formatter_agent
            )
        elif self._main_agent_type == MainAgentType.ORCHESTRATOR_ONLY:
            return OrchestratorOnlyMainAgent(
                orchestrator_agent=self._orchestrator_agent,
                formatter_agent=self._formatter_agent
            )

        # Este código no debería ejecutarse si la validación es correcta
        raise ValueError("Tipo de agente principal no implementado")
