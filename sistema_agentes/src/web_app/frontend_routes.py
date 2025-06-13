import time

from quart import Blueprint, request, jsonify
from src.web_app.agent_manager import AgentManager
from src.web_app.model_configs import get_available_models
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
    """Return available agent models for OpenWebGUI"""
    return {
        "object": "list",
        "data": get_available_models()
    }

@bp.route('/api/chat/completions', methods=['POST'])
async def completions():
    """OpenWebGUI compatible chat completions endpoint"""
    try:
        data = await request.get_json()
        if not data:
            return jsonify({"error": {"message": "No JSON data provided"}}), 400
        
        model = data.get('model', 'agente-simple')
        messages = data.get('messages', [])
        temperature = data.get('temperature', 0.7)
        max_tokens = data.get('max_tokens', 1500)  # Increased for longer responses
        stream = data.get('stream', False)

        is_valid, error_message = validate_messages_format(messages)
        if not is_valid:
            return jsonify({"error": {"message": error_message}}), 400
        print(f"Processing request with {len(messages)} messages, model: {model}")
        
        agent_manager = AgentManager.get_instance()
        result = await agent_manager.handle_query(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        if not result:
            result = "Lo siento, no pude procesar tu consulta en este momento."

        prompt_tokens, completion_tokens, total_tokens, result_content = calculate_token_usage(messages, result)

        response = {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
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

        return jsonify(response)

    except Exception as e:
        print(f"Error in completions endpoint: {str(e)}")
        return jsonify({
            "error": {
                "message": f"Internal server error: {str(e)}",
                "type": "internal_error"
            }
        }), 500
