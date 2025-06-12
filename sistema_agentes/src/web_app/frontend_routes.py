import asyncio

from flask import Blueprint, request
from main import call_agent

bp = Blueprint('api', __name__)

@bp.route('/')
def prueba():
    return "Hello, World!"

@bp.route('/call_test')
def test():
    return asyncio.run(call_agent())

@bp.route('/api/models', methods=['GET'])
def get_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "modelo-backend",
                "object": "model",
                "created": 1677652288,
                "owned_by": "mi-backend"
            }
        ]
    }

@bp.route('/api/chat/completions', methods=['POST'])
def completions():
    #result = asyncio.run(call_agent())
   try:
    data = request.get_json()
    model = data.get('model', 'default-model')
    messages = data.get('messages', [])
    temperature = data.get('temperature', 0.7)
    max_tokens = data.get('max_tokens', 150)

    # Preparar el contexto para tu agente
    conversation_history = []
    for msg in messages:
        conversation_history.append({
            'role': msg.get('role'),
            'content': msg.get('content', '')
        })

    result = asyncio.run(call_agent(
        model=model,
        messages=conversation_history,
        temperature=temperature,
        max_tokens=max_tokens
    ))

    return {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": result
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": sum(len(msg.get('content', '').split()) for msg in messages),
            "completion_tokens": len(result.split()),
            "total_tokens": sum(len(msg.get('content', '').split()) for msg in messages) + len(result.split())
        }
    }

    except Exception as e:
        return {"error": {"message": str(e)}}, 500
