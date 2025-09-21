
"""Carregador de catálogo (JSON) para injetar no prompt (LLM-first).

- Fonte: config/catalog.json
- Fornece: load_catalog(), flatten_for_prompt()
"""
from __future__ import annotations
from typing import Any, Dict, List
import json, os
from kink import di

CATALOG_PATH = os.environ.get("HB_CATALOG_PATH", "config/catalog.json")

def load_catalog() -> Dict[str, Any]:
    """Carrega o catálogo do disco. Em caso de erro, retorna estrutura padrão vazia."""
    try:
        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"currency":"BRL","categories":[], "rules":{}}

def flatten_for_prompt(cat: Dict[str, Any], max_items: int = 60) -> str:
    """Retorna string compacta do catálogo para prompt (SKU; Nome; Preço em R$; tags)."""
    lines: List[str] = []
    cur = cat.get("currency","BRL")
    count = 0
    for c in cat.get("categories", []):
        cname = c.get("name") or c.get("id","")
        for it in c.get("items", []):
            if count >= max_items:
                break
            sku = it.get("sku","")
            name = it.get("name","")
            price = it.get("price_cents",0)/100
            tags = ",".join(it.get("tags",[])[:4])
            lines.append(f"{sku} • {name} • R$ {price:.2f} • tags: {tags} • cat: {cname}")
            count += 1
    if count >= max_items:
        lines.append("… (catálogo truncado no prompt)")
    return "\n".join(lines)
