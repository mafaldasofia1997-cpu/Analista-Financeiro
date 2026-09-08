"""Armazenamento de `portfolio.json` e `notes.json`.

Dois modos, escolhidos automaticamente:

* **Local** (por omissão) — ficheiros na pasta `app/`. Usado em desenvolvimento.
* **Gist** — um GitHub Gist secreto, quando os secrets `GIST_ID` e `GITHUB_TOKEN`
  estão definidos. Necessário no alojamento (o disco do Streamlit Cloud é volátil).
  Leitura via API do Gist (cache curto); escrita via `PATCH` autenticado.
"""
from __future__ import annotations

import json
import os

import requests
import streamlit as st

from .config import APP_DIR


def secret(name: str) -> str | None:
    """Lê um valor de os.environ ou de st.secrets (o que existir)."""
    val = os.getenv(name)
    if val and val.strip():
        return val.strip()
    try:
        val = st.secrets.get(name)  # type: ignore[attr-defined]
    except Exception:
        val = None
    return str(val).strip() if val else None


def _gist_cfg() -> tuple[str, str] | None:
    gid, tok = secret("GIST_ID"), secret("GITHUB_TOKEN")
    return (gid, tok) if gid and tok else None


def storage_mode() -> str:
    return "gist" if _gist_cfg() else "local"


@st.cache_data(ttl=30, show_spinner=False)
def _gist_files(gist_id: str, token: str) -> dict[str, str]:
    r = requests.get(
        f"https://api.github.com/gists/{gist_id}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        timeout=15,
    )
    r.raise_for_status()
    return {
        name: (f or {}).get("content", "")
        for name, f in r.json().get("files", {}).items()
    }


def read_json(name: str, default):
    """Lê `name` (ex.: 'portfolio.json'). Devolve `default` se não existir/for inválido."""
    cfg = _gist_cfg()
    if cfg:
        try:
            content = _gist_files(*cfg).get(name)
            if content:
                return json.loads(content)
        except Exception:
            pass
        return default
    try:
        return json.loads((APP_DIR / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def write_json(name: str, data) -> None:
    payload = json.dumps(data, indent=2, ensure_ascii=False)
    cfg = _gist_cfg()
    if cfg:
        gist_id, token = cfg
        r = requests.patch(
            f"https://api.github.com/gists/{gist_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
            json={"files": {name: {"content": payload}}},
            timeout=15,
        )
        r.raise_for_status()
        _gist_files.clear()  # a próxima leitura vem fresca
        return
    (APP_DIR / name).write_text(payload, encoding="utf-8")
