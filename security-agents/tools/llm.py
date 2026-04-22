import requests

OLLAMA_URL = "http://ollama:11434"
DEFAULT_MODEL = "llama3.2:3b"

class LLM:
    def __init__(self, model=DEFAULT_MODEL, ollama_url=OLLAMA_URL):
        self.model = model
        self.ollama_url = ollama_url

    def generate(self, prompt: str) -> str:
        response = requests.post(
            f"{self.ollama_url}/api/chat",
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False
            },
            timeout=120
        )
        response.raise_for_status()
        return response.json()["message"]["content"]
