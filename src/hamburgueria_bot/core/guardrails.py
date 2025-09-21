
"""Guardrails simples: sanitização e heurística de revisão."""
import re

BLOCKLIST = [
    re.compile(r"(?i)(ignore .* (instructions|rules)|reveal|system prompt|bypass|jailbreak)"),
    re.compile(r"(?i)(act as .* system|you are not an ai|developer mode)"),
]

CONTROL_CHARS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")

def sanitize_text(text: str) -> str:
    """Normaliza espaços e remove caracteres de controle."""
    text = CONTROL_CHARS.sub("", text or "")
    return " ".join(text.split())

def should_force_reviewer(text: str) -> bool:
    """Heurística simples para acionar Revisor."""
    return any(p.search(text or "") for p in BLOCKLIST)
