import uuid
from typing import Dict, Optional, Any, AsyncGenerator
from enum import Enum
import time
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
            cls._instance.iterations_since_heartbeat = 0
            cls._instance.heartbeat_threshold = 50
            cls._instance.last_status = "Iniciando..."
        return cls._instance

    @classmethod
    def get_instance(cls) -> 'StreamManager':
        """Get the singleton instance of StreamManager"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def start_streaming(self):
        self._instance.is_streaming = True
        self._instance.events_sent = 0
        self._instance.event_queue = []
        self._instance.iterations_since_heartbeat = 0
        print("StreamManager: Started streaming")

    def is_streaming_active(self) -> bool:
        return self._instance.is_streaming

    def stop_streaming(self):
        self._instance.is_streaming = False

    def get_last_status(self) -> str:
        return self._instance.last_status

    def get_heartbeat_threshold(self) -> int:
        return self._instance.heartbeat_threshold

    def _update_last_status(self, status: str):
        self._instance.last_status = status

    async def consume_remaining_events(self) -> AsyncGenerator[str, None]:
        """Consume all remaining events in the queue without the streaming loop"""
        while self._instance.event_queue:
            event = self._instance.event_queue.pop(0)
            self._instance.events_sent += 1
            yield f"data: {json.dumps(event)}\n\n"

    async def stream_events(self) -> AsyncGenerator[str, None]:
        """
        Generador principal que yielda eventos en formato SSE.
        """
        while self._instance.is_streaming or self._instance.event_queue:
            if self._instance.event_queue:
                event = self._instance.event_queue.pop(0)
                self._instance.events_sent += 1
                self._instance.iterations_since_heartbeat = 0
                yield f"data: {json.dumps(event)}\n\n"
            else:
                if self._instance.is_streaming:
                    self._instance.iterations_since_heartbeat += 1
                    if self._instance.iterations_since_heartbeat >= self.get_heartbeat_threshold():
                        await self._emit_heartbeat()
                        self._instance.iterations_since_heartbeat = 0
                    await asyncio.sleep(0.1)
                else:
                    break

    def _add_event(self, openwebui_event: Dict[str, Any]):
        """Agrega un evento a la cola interna"""
        if not self.is_streaming_active():
            return

        self._instance.event_queue.append(openwebui_event)

    async def _emit_status_event(self, description: str, done: bool = False):
        self._update_last_status(description)
        openwebui_event = {
            "type": "status",
            "data": {
                "description": description,
                "done": done,
                "hidden": False
            }
        }
        self._add_event(openwebui_event)

    async def emit_agent_called(self, agent_name: str, task: Optional[str] = None):
        if task:
            await self._emit_status_event(description=f"LLamando agente {agent_name}: {task}", done=False)
        else:
            await self._emit_status_event(description=f"LLamando agente {agent_name}", done=False)

    async def emit_generation_finished(self):
        await self._emit_status_event(description="", done=True)
        self.stop_streaming()

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

        except Exception as e:
            print(f"StreamManager: Error generating planner summary: {e}")
            summary = "generando plan"

        await self.emit_agent_called(agent_name="Agente planner", task=summary)

    async def emit_formatter_generation(self, content: str):
        openwebui_event = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "agent_system",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0
            }
        }
        self._add_event(openwebui_event)

    async def emit_citation(self, citation: Citation):
        """Emite una cita/fuente"""
        if not self.is_streaming_active():
            return

        try:
            citation_id = str(uuid.uuid4())
            if citation.doc_url.startswith("http") or citation.doc_url.startswith("https"):
                openwebui_event = {
                    "type": "citation",
                    "data": {
                        "document": [citation.doc_explanation],
                        "metadata": [],
                        "source": {
                            "id": citation_id,
                            "name": citation.doc_name,
                            "url": citation.doc_url
                        }
                    }
                }
            else:
                openwebui_event = {
                    "type": "citation",
                    "data": {
                        "document": [citation.doc_explanation],
                        "metadata": [],
                        "source": {
                            "id": citation_id,
                            "name": citation.doc_url,
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

    async def _emit_heartbeat(self):
        """Emite un heartbeat para mantener viva la conexión SSE"""
        current_status = self.get_last_status()
        heartbeat_status = f"{current_status}*"
        self._update_last_status(heartbeat_status)
        
        openwebui_event = {
            "type": "status",
            "data": {
                "description": heartbeat_status,
                "done": False,
                "hidden": False
            }
        }
        self._add_event(openwebui_event)
