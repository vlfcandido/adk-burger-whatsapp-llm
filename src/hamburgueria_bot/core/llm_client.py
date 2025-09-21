
"""Cliente HTTP para LiteLLM, com validação Pydantic e suporte a tool-calling executável."""
from typing import Any, Type, Dict
import httpx, json
from pydantic import BaseModel
from kink import di
from .settings import Settings
from ..adk.runtime.toolkit import ToolRegistry

class LLMClient:
    """Cliente do gateway LiteLLM.
    Suporta: complete_json() e complete_with_tools_loop().
    """
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or di[Settings]

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=self.settings.litellm_base_url, timeout=self.settings.litellm_timeout_s)

    def complete_json(self, system: str, user: str, schema: Type[BaseModel]) -> BaseModel:
        payload = {
            "model": self.settings.litellm_model_primary,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "temperature": self.settings.litellm_temperature,
            "max_tokens": self.settings.litellm_max_tokens,
        }
        try:
            with self._client() as cli:
                r = cli.post("/chat/completions", json=payload)
                r.raise_for_status()
                data = r.json()
                content = data["choices"][0]["message"]["content"]
                return schema.model_validate_json(content)
        except Exception:
            payload["model"] = self.settings.litellm_model_fallback
            with self._client() as cli:
                r = cli.post("/chat/completions", json=payload)
                r.raise_for_status()
                data = r.json()
                content = data["choices"][0]["message"]["content"]
                return schema.model_validate_json(content)

    def complete_with_tools_loop(self, *, system: str, user: str, tools_registry: ToolRegistry, max_steps: int = 4) -> Dict[str, Any]:
        """Executa um loop de tool-calling real (com execução de funções).
        Espera que o modelo finalize com uma mensagem `assistant` (sem tool_calls) contendo o texto final
        ou JSON com {"texto": "..."}.
        Retorna a última mensagem `assistant`.
        """
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        model = self.settings.litellm_model_primary
        tools = tools_registry.openai_tools()
        steps = 0
        while True:
            payload = {
                "model": model,
                "messages": messages,
                "tools": tools,
                "tool_choice": "auto",
                "temperature": self.settings.litellm_temperature,
                "max_tokens": self.settings.litellm_max_tokens,
            }
            with self._client() as cli:
                r = cli.post("/chat/completions", json=payload)
                r.raise_for_status()
                data = r.json()
            msg = data["choices"][0]["message"]
            tool_calls = msg.get("tool_calls")
            if tool_calls:
                messages.append(msg)
                for call in tool_calls:
                    fname = call["function"]["name"]
                    fargs = call["function"].get("arguments", "{}")
                    # Executa tool e registra resposta
                    tool_result_json = tools_registry.execute_json(fname, fargs)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "name": fname,
                        "content": tool_result_json,
                    })
                steps += 1
                if steps >= max_steps:
                    # Força o modelo a finalizar
                    messages.append({"role": "system", "content": "Finalize a resposta ao cliente agora."})
                continue
            return msg
