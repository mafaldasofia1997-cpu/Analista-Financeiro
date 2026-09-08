"""Notas adicionais do utilizador (texto livre) por ação.

O dossiê da aba "Notas" é gerado automaticamente (ver `company.build_dossier`);
aqui guarda-se apenas o texto que o utilizador queira acrescentar por cima.
Guardado em `app/notes.json` como {"AAPL": "texto...", ...}.
"""
from __future__ import annotations

from . import store


def load(symbol: str) -> str:
    data = store.read_json("notes.json", {})
    if not isinstance(data, dict):
        return ""
    val = data.get(symbol, "")
    if isinstance(val, dict):  # formato antigo (secções) -> junta tudo
        return "\n\n".join(f"{k}: {v}" for k, v in val.items() if v)
    return val or ""


def save(symbol: str, text: str) -> None:
    data = store.read_json("notes.json", {})
    if not isinstance(data, dict):
        data = {}
    if text and text.strip():
        data[symbol] = text.strip()
    else:
        data.pop(symbol, None)
    store.write_json("notes.json", data)
