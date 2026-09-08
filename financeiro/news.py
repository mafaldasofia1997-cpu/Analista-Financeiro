"""Notícias das últimas 48 horas, limitadas a um conjunto de fontes financeiras.

Fontes:
  • Seeking Alpha  — feed por símbolo (direto, específico do ticker)
  • Reuters, Yahoo Finance, Finviz, Trading Economics — via Google Notícias
    com filtro `site:` + filtro de relevância pelo nome da empresa

Nenhuma exige API key. O endpoint de notícias da FMP (pago) já não é usado.
"""
from __future__ import annotations

import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import feedparser
import streamlit as st

# domínio -> nome apresentável da fonte
NEWS_DOMAINS: dict[str, str] = {
    "seekingalpha.com": "Seeking Alpha",
    "finviz.com": "Finviz",
    "reuters.com": "Reuters",
    "tradingeconomics.com": "Trading Economics",
    "finance.yahoo.com": "Yahoo Finance",
}
FONTES_LABEL = ", ".join(NEWS_DOMAINS.values())

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# sufixos societários a remover para obter o "núcleo" do nome da empresa
_SUFFIXOS = re.compile(
    r"\b(inc|incorporated|corp|corporation|company|co|ltd|limited|plc|holdings?|"
    r"group|the|and|&)\b\.?",
    re.IGNORECASE,
)


@dataclass
class NewsItem:
    title: str
    url: str
    source: str
    published_dt: datetime
    snippet: str
    image: str | None
    provider: str  # feed de origem: "Google Notícias" | "Seeking Alpha"


@st.cache_data(ttl=900, show_spinner=False)
def _fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310
        return resp.read()


def _entry_dt(entry) -> datetime | None:
    tt = entry.get("published_parsed") or entry.get("updated_parsed")
    return datetime(*tt[:6], tzinfo=timezone.utc) if tt else None


def _norm_title(title: str) -> str:
    """Chave de deduplicação: sem '(NYSE:X)', sem ' - Publisher', sem pontuação."""
    core = re.sub(r"\([^)]*\)", " ", title or "")  # (NYSE:O), (AAPL)... em qualquer sítio
    core = re.sub(r"\s+[-|–]\s+[^-|–]+$", "", core)  # ' - Publisher' final
    return re.sub(r"[^a-z0-9]+", "", core.lower())[:70]


def _clean_source(name: str) -> str:
    return "Yahoo Finance" if "yahoo" in (name or "").lower() else (name or "")


def _core_name(name: str) -> str:
    core = _SUFFIXOS.sub(" ", name or "")
    core = re.sub(r"[.,]", " ", core)
    return re.sub(r"\s+", " ", core).strip()


def _relevance_tokens(company: str, symbol: str) -> list[str]:
    toks = [t for t in _core_name(company).lower().split() if len(t) > 2]
    return toks or [symbol.lower()]


def _is_relevant(title: str, tokens: list[str]) -> bool:
    t = title.lower()
    return all(tok in t for tok in tokens)


def _from_google(symbol: str, company: str, tokens: list[str], cutoff: datetime) -> list[NewsItem]:
    core = _core_name(company)
    who = f'"{core}"' if core else symbol
    sites = " OR ".join(f"site:{d}" for d in NEWS_DOMAINS)
    q = f"({who}) ({sites}) when:2d"
    url = (
        "https://news.google.com/rss/search?q="
        + urllib.parse.quote(q)
        + "&hl=en-US&gl=US&ceid=US:en"
    )
    try:
        parsed = feedparser.parse(_fetch(url))
    except Exception:
        return []

    items: list[NewsItem] = []
    for e in parsed.entries:
        dt = _entry_dt(e)
        if not dt or dt < cutoff:
            continue
        title = e.get("title") or "(sem título)"
        if not _is_relevant(title, tokens):
            continue
        src = ""
        raw_src = e.get("source")
        if isinstance(raw_src, dict):
            src = raw_src.get("title", "")
        items.append(
            NewsItem(
                title=title,
                url=e.get("link") or "",
                source=_clean_source(src) or "Google Notícias",
                published_dt=dt,
                snippet="",
                image=None,
                provider="Google Notícias",
            )
        )
    return items


def _from_seeking_alpha(symbol: str, cutoff: datetime) -> list[NewsItem]:
    url = f"https://seekingalpha.com/api/sa/combined/{symbol}.xml"
    try:
        parsed = feedparser.parse(_fetch(url))
    except Exception:
        return []

    items: list[NewsItem] = []
    for e in parsed.entries:
        dt = _entry_dt(e)
        if not dt or dt < cutoff:
            continue
        items.append(
            NewsItem(
                title=e.get("title") or "(sem título)",
                url=e.get("link") or "",
                source="Seeking Alpha",
                published_dt=dt,
                snippet=re.sub("<[^<]+?>", "", e.get("summary", ""))[:300],
                image=None,
                provider="Seeking Alpha",
            )
        )
    return items


def get_recent_news(
    symbol: str, company_name: str, hours: int = 48
) -> list[NewsItem]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    tokens = _relevance_tokens(company_name, symbol)

    collected: list[NewsItem] = []
    collected += _from_google(symbol, company_name, tokens, cutoff)
    collected += _from_seeking_alpha(symbol, cutoff)

    # deduplicação por título normalizado (mantém a mais recente)
    seen: set[str] = set()
    unique: list[NewsItem] = []
    for item in sorted(collected, key=lambda x: x.published_dt, reverse=True):
        key = _norm_title(item.title)
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique
