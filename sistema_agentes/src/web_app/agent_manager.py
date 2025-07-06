from typing import Dict, List, Optional

from src.dummy_agent_graph import DummyAgent
from src.main_agent.main_agent_builder import FlexibleAgentBuilder
from src.main_agent.main_graph import MainAgent
from src.specialized_agents.code_agent.code_agent_graph import CodeAgent
from src.difficulty_classifier_agent.double_main_agent import DoubleMainAgent
from src.difficulty_classifier_agent.difficulty_classifier_graph import ClassifierAgent
from src.mcp_client.mcp_multi_client import MCPClient
from src.specialized_agents.confluence_agent.confluence_agent_graph import CachedConfluenceAgent
from src.specialized_agents.filesystem_agent.filesystem_agent_graph import FileSystemAgent
from src.specialized_agents.gitlab_agent.gitlab_agent_graph import GitlabAgent
from src.specialized_agents.google_drive_agent.google_drive_agent_graph import GoogleDriveAgent
from src.web_app.model_configs import get_model_configuration


class AgentManager:
    """
    Singleton manager for initializing and managing agents in the web application.
    Handles MCP connections, specialized agent initialization, and main agent factory.
    """
    
    _instance: Optional['AgentManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AgentManager, cls).__new__(cls)
            cls._instance.available_agents = []
            cls._instance.main_agents_cache = {}
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> 'AgentManager':
        """Get the singleton instance of AgentManager"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def initialize(self):
        """
        Initialize the AgentManager by initializing specialized agents
        """
        specialized_agents = [
            # Claude agent, do not uncomment this
            CodeAgent(use_memory=False),
            CachedConfluenceAgent(use_memory=False),
            FileSystemAgent(use_memory=False),
            GoogleDriveAgent(use_memory=False),
            GitlabAgent(use_memory=False)
        ]
        
        for agent in specialized_agents:
            try:
                await agent.init_agent()
                self.available_agents.append(agent)
                print(f"Successfully initialized {agent.name}")
            except Exception as e:
                print(f"Error initializing agent {agent.name}: {e}")
        
        print(f"AgentManager initialized with {len(self.available_agents)} available agents")
    
    
    async def get_or_create_main_agent(self, model: str = None) -> MainAgent:
        """
        Get or create a main agent using singleton pattern.
        If the agent type was already created, return the existing instance.
        """
        config = get_model_configuration(model)
        
        # Create cache key based on configuration
        if config.use_double_agent:
            cache_key = "double_agent"
        else:
            cache_key = f"{getattr(config.main_type, 'value', 'none')}_{getattr(config.planner_type, 'value', 'none')}_{getattr(config.orchestrator_type, 'value', 'none')}"
        
        if cache_key in self.main_agents_cache:
            print(f"Returning cached agent for configuration: {cache_key}")
            return self.main_agents_cache[cache_key]
        
        print(f"Creating new agent for configuration: {cache_key}")
        
        if config.use_double_agent:
            agent = await self._create_double_main_agent()
        # Este if no es nada limpio, habría que abstraer
        elif not config.main_type:
            agent = DummyAgent()
        else:
            builder = FlexibleAgentBuilder()
            agent = await (await (builder
                           .reset()
                           .with_main_agent_type(config.main_type.value)
                           .with_planner_type(config.planner_type.value)
                           .with_orchestrator_type(config.orchestrator_type.value)
                           .with_specialized_agents(self.available_agents)
                           .initialize_skipping_specialized_agents_initialization())).build()
        self.main_agents_cache[cache_key] = agent
        
        return agent
    
    async def _create_double_main_agent(self) -> DoubleMainAgent:
        """Create and initialize the double main agent"""
        print("Creating double main agent...")
        
        # Create simple agent
        builder_simple = FlexibleAgentBuilder()
        builder_simple.with_main_agent_type("orchestrator_only") \
            .with_planner_type("none") \
            .with_orchestrator_type("react") \
            .with_specialized_agents(self.available_agents)
        await builder_simple.initialize_skipping_specialized_agents_initialization()
        simple_agent = await builder_simple.build()

        # Create complex agent
        builder_complex = FlexibleAgentBuilder()
        builder_complex.with_main_agent_type("basic") \
            .with_planner_type("orchestrator_planner") \
            .with_orchestrator_type("dummy") \
            .with_specialized_agents(self.available_agents)
        await builder_complex.initialize_skipping_specialized_agents_initialization()
        complex_agent = await builder_complex.build()

        # Create classifier agent
        classifier_agent = ClassifierAgent(use_tuned_model=True)

        # Create double main agent
        double_main_agent = DoubleMainAgent(
            classifier_agent=classifier_agent,
            simple_main_agent=simple_agent,
            complex_main_agent=complex_agent
        )
        await double_main_agent.init_memory_store()

        return double_main_agent
    
    async def handle_query(self, model: str = None, messages: List = None, temperature: float = 0.7, max_tokens: int = 150):
        """
        Handle a user query using the appropriate agent
        """
        try:
            conversation_messages = []
            
            if messages and len(messages) > 0:
                # Get the latest user message as the main query
                for msg in reversed(messages):
                    if msg.get('role') == 'user':
                        query = msg.get('content')
                        break
                
                # Prepare conversation history for the agent (exclude the current query)
                conversation_messages = [
                    {"role": msg.get('role'), "content": msg.get('content', '')}
                    for msg in messages[:-1]
                ]

            # Get the appropriate agent
            agent = await self.get_or_create_main_agent(model)
            
            # Execute the agent (StreamManager handles streaming internally)
            result = await agent.execute_agent_graph_with_exception_handling({
                "query": query,
                "messages": conversation_messages
            })
            result = agent.process_result(result)
            return result

        except Exception as e:
            print(f"Error en handle_query: {str(e)}")
            return f"Error ejecutando el agente: {str(e)}"
    
    async def cleanup(self):
        """
        Clean up all resources: agents and MCP connections
        """

        # Cleanup MCP client (closes async global stack)
        try:
            await MCPClient.cleanup()
        except Exception as e:
            print(f"Error cleaning up MCP client: {e}")
        
        # Clear cache
        self.main_agents_cache.clear()

    @classmethod
    async def clean(cls):
        """
        Clean up the singleton instance
        """
        if cls._instance is not None:
            await cls._instance.cleanup()
    
    def get_available_agents_info(self) -> List[str]:
        """Get information about available agents"""
        return [f"{agent.name}: {agent.description}" for agent in self.available_agents]