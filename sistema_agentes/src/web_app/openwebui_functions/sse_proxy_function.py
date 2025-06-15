import json
from pydantic import BaseModel, Field
import requests

class Pipe:
    class Valves(BaseModel):
        BACKEND_URL: str = Field(
            # Llamar a host desde dentro del docker
            default=f"http://172.17.0.1:5000",
            description="sistema agentes backend url"
        )
        REQUEST_TIMEOUT: int = Field(
            default=300,
            description="Timeout en segundos para requests al backend"
        )

    def __init__(self):
        self.valves = self.Valves()

    def pipes(self):
        #todo: que llame al backend para que obtenga los modelos
        return [{
            "id": "modelo_backend",
            "name": "Modelo Backend"
        }]

    async def pipe(self, body: dict, __user__: dict, __event_emitter__):
        self.print_log("Iniciando pipe")
        headers = {
            "Content-Type": "application/json",
        }
        model_id = body["model"][body["model"].find(".") + 1 :]
        # Payload es post http body, antes de establecer sse
        payload = {**body, "model": model_id}

        try:
            r = requests.post(
                url=f"{self.valves.BACKEND_URL}/api/chat/completions",
                json=payload,
                headers=headers,
                stream=True,
            )

            r.raise_for_status()

            if body.get("stream", False):
                self.print_log("STREAM==TRUE")
                return self._process_streaming_response(r, __event_emitter__)
            else:
                self.print_log("STREAM==FALSE")
                return r.json()
        except Exception as e:
            return f"Error: {e}"

    async def _process_streaming_response(self, response, __event_emitter__):
        self.print_log("Manejando respuesta SSE")
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                self.print_log(f"LINE_STR: {line_str}")

                if line_str.startswith('data: '):
                    data_str = line_str[6:]
                    self.print_log(f"DATA_STR: {data_str}")

                    if data_str.strip() == '[DONE]':
                        break

                    try:
                        data = json.loads(data_str)
                        self.print_log(f"DATA: {json.dumps(data)}")

                        # Verificar si es un evento personalizado de OpenWebUI
                        if self._is_openwebui_event(data):
                            await __event_emitter__(data)
                        else:
                            # Es un mensaje normal de OpenAI, devolverlo como stream
                            yield f"data: {data_str}\n\n"

                    except json.JSONDecodeError:
                        # Si no es JSON válido, pasarlo tal como está
                        yield f"data: {data_str}\n\n"
                else:
                    yield f"{line_str}\n"
        yield "data: [DONE]\n\n"

    def _is_openwebui_event(self, data):
        if not isinstance(data, dict):
            return False

        # Lista de tipos de eventos conocidos de OpenWebUI
        openwebui_event_types = [
            "status", "chat:completion", "chat:message:delta", "message",
            "chat:message", "replace", "chat:message:files", "files",
            "chat:title", "chat:tags", "source", "citation", "notification",
            "confirmation", "input", "execute"
        ]

        return (
            "type" in data and
            "data" in data and
            data["type"] in openwebui_event_types
        )

    def print_log(self, log: str):
        print(f"+++TRAZA: {log}+++")