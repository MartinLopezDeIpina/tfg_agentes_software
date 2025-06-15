from typing import Dict, Optional, Any, AsyncGenerator
from enum import Enum
from datetime import datetime
from langchain_core.messages import SystemMessage
from config import dummy_llm
from src.specialized_agents.citations_tool.models import Citation
import json
import asyncio

from static.prompts import PLANNER_SUMMARY_PROMPT


class StreamEventType(Enum):
    AGENT_CALLED = "status"
    PLANNER_ACTIVITY = "status"
    FORMATTER_GENERATION = "chat:message:delta"
    CITATION = "source"
    ERROR = "notification"


class StreamManager:
    """
    Singleton manager para manejar eventos de streaming.
    Los agentes llaman a los métodos emit_*, que agregan eventos a una cola interna.
    El generador de streaming consume estos eventos.
    """

    _instance: Optional['StreamManager'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StreamManager, cls).__new__(cls)
            cls._instance.is_streaming = False
            cls._instance.events_sent = 0
            cls._instance.dummy_llm = dummy_llm
            cls._instance.event_queue = []
            cls._instance._stream_generator = None
        return cls._instance

    @classmethod
    def get_instance(cls) -> 'StreamManager':
        """Get the singleton instance of StreamManager"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def start_streaming(self):
        self.is_streaming = True
        self.events_sent = 0
        self.event_queue = []
        print("StreamManager: Started streaming")

    def stop_streaming(self):
        if self.is_streaming:
            print(f"StreamManager: Stopped streaming. Events sent: {self.events_sent}")
        self.is_streaming = False
        self.events_sent = 0
        self.event_queue = []

    def is_streaming_active(self) -> bool:
        return self.is_streaming

    async def stream_events(self) -> AsyncGenerator[str, None]:
        """
        Generador principal que yielda eventos en formato SSE.
        """
        empty_cycles = 0
        max_empty_cycles = 10  # Número de ciclos vacíos antes de terminar

        while self.is_streaming or self.event_queue:
            if self.event_queue:
                event = self.event_queue.pop(0)
                self.events_sent += 1
                empty_cycles = 0  # Reset counter cuando hay eventos
                yield f"data: {json.dumps(event)}\n\n"
            else:
                # Si no hay eventos y el streaming está activo, esperar
                if self.is_streaming:
                    await asyncio.sleep(0.01)
                else:
                    # Si el streaming terminó, incrementar contador
                    empty_cycles += 1
                    if empty_cycles >= max_empty_cycles:
                        break
                    await asyncio.sleep(0.01)

    def _add_event(self, openwebui_event: Dict[str, Any]):
        """Agrega un evento a la cola interna"""
        if not self.is_streaming_active():
            return

        self.event_queue.append(openwebui_event)

    async def emit_agent_called(self, agent_name: str):
        openwebui_event = {
            "type": "status",
            "data": {
                "description": f"Llamando agente {agent_name}",
                "done": False,
                "hidden": False
            }
        }
        self._add_event(openwebui_event)

    async def emit_planner_activity(self, plan_content: str, activity_description: str = ""):
        """Emite evento de actividad del planner con resumen del plan"""
        if not self.is_streaming_active():
            return

        try:
            summary_prompt = PLANNER_SUMMARY_PROMPT.format(plan_content=plan_content)
            summary_result = await self.dummy_llm.ainvoke(
                [SystemMessage(content=summary_prompt)],
            )
            summary = summary_result.content if hasattr(summary_result, 'content') else str(summary_result)
            description = f"Agente planner: {summary.strip()}"

        except Exception as e:
            print(f"StreamManager: Error generating planner summary: {e}")
            description = f"Agente planner: {activity_description or 'generando plan'}"

        openwebui_event = {
            "type": "status",
            "data": {
                "description": description,
                "done": False,
                "hidden": False
            }
        }
        self._add_event(openwebui_event)

    async def emit_formatter_generation(self, partial_content: str, is_complete: bool = False):
        """Emite eventos de generación en tiempo real del formatter"""
        if is_complete:
            openwebui_event = {
                "type": "chat:message",
                "data": {
                    "content": partial_content
                }
            }
        else:
            openwebui_event = {
                "type": "chat:message:delta",
                "data": {
                    "content": partial_content
                }
            }

        self._add_event(openwebui_event)

    async def emit_citation(self, citation: Citation):
        """Emite una cita/fuente"""
        if not self.is_streaming_active():
            return

        try:
            openwebui_event = {
                "type": "source",
                "data": {
                    "document": [citation.doc_explanation],
                    "metadata": [],
                    "source": {
                        "name": citation.doc_name,
                        "source": citation.doc_url
                    }
                }
            }
            self._add_event(openwebui_event)

        except Exception as e:
            print(f"StreamManager: Error processing citation: {e}")
            # Fallback a notificación de error
            await self.emit_error("Error al procesar cita")

    async def emit_error(self, error_message: str, agent_name: str = ""):
        """Emite un error como notificación"""
        message = f"Error en {agent_name}: {error_message}" if agent_name else f"Error: {error_message}"

        openwebui_event = {
            "type": "notification",
            "data": {
                "type": "error",
                "content": message
            }
        }
        self._add_event(openwebui_event)

    async def emit_notification(self, message: str, notification_type: str = "info"):
        """Emite una notificación general"""
        openwebui_event = {
            "type": "notification",
            "data": {
                "type": notification_type,
                "content": message
            }
        }
        self._add_event(openwebui_event)

    async def cleanup(self):
        """Limpia el estado del streaming"""
        if self.is_streaming:
            self.stop_streaming()