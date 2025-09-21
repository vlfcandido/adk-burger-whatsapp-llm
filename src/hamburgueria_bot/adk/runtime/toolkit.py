
"""Toolkit: registro de tools tipadas (Pydantic) e execução de chamadas."""
from __future__ import annotations
from typing import Callable, Dict, Any, Type
from pydantic import BaseModel
import json

class ToolSpec(BaseModel):
    name: str
    description: str
    args_schema: Type[BaseModel]
    func: Callable[[BaseModel], Any]

    def to_openai_function(self) -> dict:
        """Converte para schema de tool (OpenAI/LiteLLM style)."""
        schema = self.args_schema.model_json_schema()
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": schema,
            },
        }

class ToolRegistry:
    """Registro de tools disponíveis para um agente."""
    def __init__(self):
        self._tools: Dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            raise ValueError(f"tool duplicada: {spec.name}")
        self._tools[spec.name] = spec

    def list_specs(self) -> list[ToolSpec]:
        return list(self._tools.values())

    def openai_tools(self) -> list[dict]:
        return [t.to_openai_function() for t in self._tools.values()]

    def execute(self, name: str, arguments: dict) -> Any:
        if name not in self._tools:
            raise KeyError(name)
        model = self._tools[name].args_schema.model_validate(arguments)
        return self._tools[name].func(model)

    def execute_json(self, name: str, arguments_json: str) -> str:
        """Executa tool recebendo `arguments` como JSON string e retorna JSON string do resultado."""
        try:
            args = json.loads(arguments_json or "{}")
        except Exception:
            args = {}
        result = self.execute(name, args)
        try:
            return json.dumps(result, ensure_ascii=False)
        except Exception:
            return json.dumps({"result": str(result)}, ensure_ascii=False)
