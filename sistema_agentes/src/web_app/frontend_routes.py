import json
import uuid
import asyncio
import time

from langchain_core.messages import BaseMessage
from quart import Blueprint, request, jsonify, Response

from src.specialized_agents.citations_tool.models import Citation
from src.web_app.agent_manager import AgentManager
from src.web_app.model_configs import get_available_models, get_tasks_model
from src.web_app.stream_manager import StreamManager
from src.utils import validate_messages_format, calculate_token_usage

bp = Blueprint('api', __name__)


@bp.route('/')
def prueba():
    return "Hello, World!"


@bp.route('/call_test')
async def test():
    agent_manager = AgentManager.get_instance()
    return await agent_manager.handle_query(
        model="agente-simple",
        messages=[{"role": "user", "content": "¿Cómo se gestionan las migraciones de la base de datos?"}]
    )

@bp.route('/api/models', methods=['GET'])
def get_models():
    return {
        "object": "list",
        "data": get_tasks_model()
    }

@bp.route('/api/models_streaming', methods=['GET'])
def get_models_streaming():
    """Return available agent models for OpenWebGUI"""
    return {
        "object": "list",
        "data": get_available_models()
    }

@bp.route('/api/chat/completions', methods=['POST'])
async def completions():
    """OpenWebGUI compatible chat completions endpoint with streaming support"""
    try:
        data = await request.get_json()
        if not data:
            return jsonify({"error": {"message": "No JSON data provided"}}), 400

        model = data.get('model', 'agente-simple')
        messages = data.get('messages', [])
        temperature = data.get('temperature', 0.7)
        max_tokens = data.get('max_tokens', 1500)
        stream = data.get('stream', False)

        is_valid, error_message = validate_messages_format(messages)
        if not is_valid:
            return jsonify({"error": {"message": error_message}}), 400

        print(f"Processing request with {len(messages)} messages, model: {model}, stream: {stream}")

        if stream:
            return await handle_streaming_completion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
        else:
            return await handle_non_streaming_completion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )

    except Exception as e:
        print(f"Error in completions endpoint: {str(e)}")
        return jsonify({
            "error": {
                "message": f"Internal server error: {str(e)}",
                "type": "internal_error"
            }
        }), 500


async def handle_non_streaming_completion(model: str, messages: list, temperature: float, max_tokens: int):
    agent_manager = AgentManager.get_instance()
    result = await agent_manager.handle_query(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens
    )
    if not result:
        result = "Lo siento, no pude procesar tu consulta en este momento."
    if isinstance(result, BaseMessage):
        result = result.content

    prompt_tokens, completion_tokens, total_tokens, result_content = calculate_token_usage(messages, result)

    response = format_chat_completion_message(
        model=model,
        result_content=result,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens
    )
    return jsonify(response)

async def handle_streaming_completion(model: str, messages: list, temperature: float, max_tokens: int):
    async def stream_generator():

        stream_manager = StreamManager.get_instance()
        agent_manager = AgentManager.get_instance()

        try:
            stream_manager.start_streaming()
            agent_task = asyncio.create_task(
                agent_manager.handle_query(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            )

            async for event in stream_manager.stream_events():
                yield event

        except Exception as e:
            await stream_manager.emit_error(error_message=str(e), agent_name="main_agent")
            print(f"Streaming error: {e}")
        finally:
            stream_manager.stop_streaming()
            yield "data: [DONE]\n\n"

    return Response(
        stream_generator(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Content-Type': 'text/event-stream; charset=utf-8'
        }
    )

def format_chat_completion_message(model: str, result_content: str, prompt_tokens: int = 0, completion_tokens: int = 0,
                                   total_tokens: int = 0) -> dict:
    """Format a chat completion message in OpenAI API format"""
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": result_content
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens
        }
    }

async def test_stream():
    stream_manager = StreamManager.get_instance()
    stream_manager.start_streaming()

    await stream_manager.emit_agent_called("agente-test")
    await asyncio.sleep(1)

    await stream_manager.emit_planner_activity("Plan de prueba para validar funcionamiento", "planificando")
    await asyncio.sleep(1)

    cita = Citation(
        doc_name="Documentación Test",
        doc_url="https://example.com/test",
        doc_explanation="Cita de prueba para validar formato"
    )
    await stream_manager.emit_citation(cita)
    await asyncio.sleep(1)

    await stream_manager.emit_formatter_generation("Contenido parcial...", is_complete=False)
    await asyncio.sleep(1)

    await stream_manager.emit_formatter_generation("Respuesta completa de prueba.", is_complete=True)
    await asyncio.sleep(1)

    await stream_manager.emit_notification("Proceso completado exitosamente", "success")
    await asyncio.sleep(1)

    stream_manager.stop_streaming()
