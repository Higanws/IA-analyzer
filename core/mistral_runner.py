import requests
import json

class MistralRunner:
    def __init__(self, api_url="http://localhost:11434", model_name="qwen2.5-7b-instruct-1m"):
        self.api_url = api_url.rstrip("/") + "/v1/chat/completions"
        self.model_name = model_name

    def enviar_prompt(self, prompt: str) -> str:
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 7000,
            "stream": False
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            respuesta_llm = response.json()
            return respuesta_llm["choices"][0]["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"Error al conectar con el LLM: {e}")
