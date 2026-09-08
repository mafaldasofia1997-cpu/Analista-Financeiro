"""Camada única de acesso à API "stable" da Financial Modeling Prep.

Todas as funções públicas têm cache (`st.cache_data`) com TTL adequado à
volatilidade do dado. Erros da FMP são convertidos em `FMPError` com mensagem
legível para a UI apanhar e mostrar.
"""
from __future__ import annotations

from datetime import date, timedelta

import requests
import streamlit as st

from .config import BASE, get_api_key


class FMPError(Exception):
    """Erro legível vindo da FMP (key inválida, limite, endpoint pago...)."""


def _get(path: str, params: dict | None = None):
    key = get_api_key()
    if not key:
        raise FMPError(
            "Falta a FMP_API_KEY. Cria o ficheiro .env a partir de .env.example."
        )
    params = dict(params or {})
    params["apikey"] = key
    url = f"{BASE}/{path.lstrip('/')}"
    try:
        resp = requests.get(url, params=params, timeout=15)
    except requests.RequestException as exc:
        raise FMPError(f"Erro de rede ao contactar a FMP: {exc}") from exc

    if resp.status_code == 401:
        raise FMPError("API key inválida. Confirma o valor de FMP_API_KEY no .env.")
    if resp.status_code in (402, 403):
        raise FMPError(
            "Este endpoint não está disponível no teu plano da FMP (requer plano pago)."
        )
    if resp.status_code == 429:
        raise FMPError(
            "Limite de pedidos da FMP atingido (plano gratuito ~250/dia). Tenta mais tarde."
        )
    if resp.status_code >= 400:
        raise FMPError(f"A FMP respondeu com HTTP {resp.status_code}.")

    try:
        data = resp.json()
    except ValueError as exc:
        raise FMPError("Resposta inesperada (não-JSON) da FMP.") from exc

    if isinstance(data, dict) and ("Error Message" in data or "error" in data):
        raise FMPError(data.get("Error Message") or data.get("error") or "Erro da FMP.")
    return data


@st.cache_data(ttl=86_400, show_spinner=False)
def search_symbol(query: str) -> list[dict]:
    """Junta resultados de pesquisa por nome e por ticker, sem duplicados."""
    q = (query or "").strip()
    if not q:
        return []
    merged: dict[str, dict] = {}
    for endpoint in ("search-name", "search-symbol"):
        try:
            rows = _get(endpoint, {"query": q, "limit": 20}) or []
        except FMPError:
            rows = []
        for r in rows:
            sym = r.get("symbol")
            if sym and sym not in merged:
                merged[sym] = r
    return list(merged.values())


@st.cache_data(ttl=43_200, show_spinner=False)
def get_profile(symbol: str) -> dict:
    data = _get("profile", {"symbol": symbol})
    if not data:
        raise FMPError(
            f"Sem perfil para '{symbol}'. O símbolo pode não existir ou não estar "
            "coberto no teu plano da FMP (cobertura sobretudo EUA)."
        )
    return data[0]


@st.cache_data(ttl=300, show_spinner=False)
def get_quote(symbol: str) -> dict:
    data = _get("quote", {"symbol": symbol})
    if not data:
        raise FMPError(f"Sem cotação para '{symbol}'.")
    return data[0]


# O plano gratuito da FMP limita os endpoints de demonstrações a 5 períodos.
MAX_PERIODOS = 5


@st.cache_data(ttl=43_200, show_spinner=False)
def _statement(kind: str, symbol: str, period: str, limit: int = MAX_PERIODOS) -> list[dict]:
    if period not in ("annual", "quarter"):
        raise ValueError(period)
    limit = min(limit, MAX_PERIODOS)
    return _get(kind, {"symbol": symbol, "period": period, "limit": limit}) or []


def get_income_statement(symbol: str, period: str) -> list[dict]:
    return _statement("income-statement", symbol, period)


def get_balance_sheet(symbol: str, period: str) -> list[dict]:
    return _statement("balance-sheet-statement", symbol, period)


def get_cash_flow(symbol: str, period: str) -> list[dict]:
    return _statement("cash-flow-statement", symbol, period)


def get_key_metrics(symbol: str, period: str) -> list[dict]:
    return _statement("key-metrics", symbol, period)


def get_ratios(symbol: str, period: str) -> list[dict]:
    return _statement("ratios", symbol, period)


@st.cache_data(ttl=21_600, show_spinner=False)
def get_price_history(symbol: str, days: int = 730) -> list[dict]:
    today = date.today()
    params = {
        "symbol": symbol,
        "from": (today - timedelta(days=days)).isoformat(),
        "to": today.isoformat(),
    }
    data = _get("historical-price-eod/full", params)
    if isinstance(data, dict):  # tolerância a formatos antigos
        return data.get("historical", []) or []
    return data or []


@st.cache_data(ttl=900, show_spinner=False)
def get_stock_news(symbol: str, limit: int = 100) -> list[dict]:
    return _get("news/stock-latest", {"symbols": symbol, "limit": limit}) or []
