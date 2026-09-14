"""Yahoo Finance (endpoint não-oficial, sem chave) — usado como fonte alternativa
gratuita quando a FMP está bloqueada para um símbolo ou a quota diária esgota.

Não substitui a FMP como fonte principal de demonstrações financeiras — serve só
para cotação/preço, que a Yahoo dá de graça e sem o limite de 250 pedidos/dia.
"""
from __future__ import annotations

from datetime import date, timedelta

import requests
import streamlit as st

_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"
_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


class YahooError(Exception):
    pass


def _chart(symbol: str, interval: str, range_: str) -> dict:
    r = requests.get(
        f"{_BASE}/{symbol}",
        params={"interval": interval, "range": range_},
        headers=_UA,
        timeout=20,
    )
    if r.status_code != 200:
        raise YahooError(f"Yahoo Finance devolveu HTTP {r.status_code} para {symbol}.")
    data = r.json()
    result = (data.get("chart") or {}).get("result")
    if not result:
        err = (data.get("chart") or {}).get("error")
        raise YahooError(f"Sem dados da Yahoo Finance para {symbol}: {err}")
    return result[0]


@st.cache_data(ttl=300, show_spinner=False)
def get_quote_free(symbol: str) -> dict:
    """Cotação atual — sem capitalização (a Yahoo não a dá neste endpoint leve)."""
    meta = _chart(symbol, "1d", "5d").get("meta", {})
    price = meta.get("regularMarketPrice")
    prev = meta.get("chartPreviousClose") or meta.get("previousClose")
    change_pct = None
    if price is not None and prev:
        change_pct = (price - prev) / prev * 100
    return {
        "price": price,
        "changePercentage": change_pct,
        "yearHigh": meta.get("fiftyTwoWeekHigh"),
        "yearLow": meta.get("fiftyTwoWeekLow"),
        "marketCap": None,
        "name": meta.get("longName") or meta.get("shortName"),
        "currency": meta.get("currency"),
    }


@st.cache_data(ttl=21_600, show_spinner=False)
def get_price_history_free(symbol: str, days: int = 730) -> list[dict]:
    """Fecho diário (~2 anos ou menos) — para o gráfico da Visão Geral."""
    range_ = "1y" if days <= 370 else ("2y" if days <= 740 else "5y")
    result = _chart(symbol, "1d", range_)
    return _to_rows(result)


@st.cache_data(ttl=43_200, show_spinner=False)
def get_price_history_deep_free(symbol: str, years: int = 20) -> list[dict]:
    """Fecho semanal de longo prazo — para cruzar com o histórico anual da SEC EDGAR."""
    result = _chart(symbol, "1wk", "max")
    rows = _to_rows(result)
    cutoff = (date.today() - timedelta(days=int(years * 365.25) + 30)).isoformat()
    return [r for r in rows if r["date"] >= cutoff]


def _to_rows(result: dict) -> list[dict]:
    ts = result.get("timestamp") or []
    ind = result.get("indicators") or {}
    closes = ((ind.get("adjclose") or [{}])[0]).get("adjclose")
    if not closes:
        closes = ((ind.get("quote") or [{}])[0]).get("close") or []
    rows = []
    for t, c in zip(ts, closes):
        if c is None:
            continue
        d = date.fromtimestamp(t).isoformat()
        rows.append({"date": d, "close": c})
    rows.sort(key=lambda r: r["date"], reverse=True)
    return rows
