"""Configuração: carrega a API key da FMP e define os endpoints base."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

APP_DIR = Path(__file__).resolve().parent.parent
BASE = "https://financialmodelingprep.com/stable"


def get_api_key() -> str | None:
    """Devolve a FMP_API_KEY de .env ou de st.secrets, ou None se não existir."""
    key = os.getenv("FMP_API_KEY")
    if key and key.strip():
        return key.strip()
    try:  # st.secrets só funciona dentro de um contexto Streamlit
        import streamlit as st

        secret = st.secrets.get("FMP_API_KEY")  # type: ignore[attr-defined]
        if secret and str(secret).strip():
            return str(secret).strip()
    except Exception:
        pass
    return None
