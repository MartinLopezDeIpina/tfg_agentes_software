import time

from quart import Blueprint, request, jsonify
from src.web_app.agent_manager import AgentManager
from src.web_app.model_configs import get_available_models

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
        
        model = data.get('model', 'agente-backend')
        messages = data.get('messages', [])
        temperature = data.get('temperature', 0.7)
        max_tokens = data.get('max_tokens', 1500)  # Increased for longer responses
        stream = data.get('stream', False)

        if not messages:
            return jsonify({"error": {"message": "No messages provided"}}), 400

        # Validate messages format
        for msg in messages:
            if 'role' not in msg or 'content' not in msg:
                return jsonify({"error": {"message": "Invalid message format"}}), 400

        print(f"Processing request with {len(messages)} messages, model: {model}")
        
        # Call the agentic system using AgentManager
        agent_manager = AgentManager.get_instance()
        result = await agent_manager.handle_query(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        if not result:
            result = "Lo siento, no pude procesar tu consulta en este momento."

        # Calculate token usage (approximate) - handle CitedAIMessage
        prompt_content = ' '.join([msg.get('content', '') for msg in messages])
        prompt_tokens = len(prompt_content.split())
        
        # Handle CitedAIMessage objects for token calculation
        if hasattr(result, 'content'):
            # It's a CitedAIMessage, extract content
            completion_tokens = len(str(result.content).split())
            result_content = str(result.content)
        else:
            # It's already a string
            completion_tokens = len(str(result).split())
            result_content = str(result)
            
        total_tokens = prompt_tokens + completion_tokens

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
