"""SEC EDGAR — histórico anual longo (10-15+ anos) para empresas dos EUA.

Usa a API pública `companyfacts` (dados XBRL dos relatórios), sem chave nem
limites relevantes. Precisa do CIK da empresa (vem no `profile` da FMP).
"""
from __future__ import annotations

from datetime import date

import pandas as pd
import requests
import streamlit as st

from .store import secret

_BASE = "https://data.sec.gov"


def _ua() -> str:
    # A SEC exige um User-Agent com contacto (nome + email). Configurável via
    # secret SEC_CONTACT; o valor por omissão cumpre o formato exigido.
    return secret("SEC_CONTACT") or (
        "Analista Financeiro app admin@analista-financeiro.app"
    )


@st.cache_data(ttl=86_400, show_spinner=False)
def company_facts(cik: str) -> dict:
    cik10 = str(cik).lstrip("CIK").zfill(10)
    r = requests.get(
        f"{_BASE}/api/xbrl/companyfacts/CIK{cik10}.json",
        headers={
            "User-Agent": _ua(),
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
        },
        timeout=45,
    )
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=86_400, show_spinner=False)
def latest_10k(cik: str) -> dict | None:
    cik10 = str(cik).lstrip("CIK").zfill(10)
    r = requests.get(
        f"{_BASE}/submissions/CIK{cik10}.json",
        headers={"User-Agent": _ua(), "Accept": "application/json"},
        timeout=30,
    )
    r.raise_for_status()
    rec = r.json().get("filings", {}).get("recent", {})
    for i, form in enumerate(rec.get("form", [])):
        if form == "10-K":
            acc = rec["accessionNumber"][i].replace("-", "")
            doc = rec["primaryDocument"][i]
            return {
                "date": rec["filingDate"][i],
                "url": f"https://www.sec.gov/Archives/edgar/data/{int(cik10)}/{acc}/{doc}",
            }
    return None


# conceito interno -> (lista de tags XBRL candidatas, unidade)
_CONCEPTS: dict[str, tuple[list[str], str]] = {
    "revenue": (
        ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues",
         "SalesRevenueNet", "SalesRevenueGoodsNet"],
        "USD",
    ),
    "grossProfit": (["GrossProfit"], "USD"),
    "operatingIncome": (["OperatingIncomeLoss"], "USD"),
    "netIncome": (["NetIncomeLoss", "ProfitLoss"], "USD"),
    "eps": (["EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted"], "USD/shares"),
    "weightedAverageShsOutDil": (
        ["WeightedAverageNumberOfDilutedSharesOutstanding",
         "WeightedAverageNumberOfSharesOutstandingBasicAndDiluted"],
        "shares",
    ),
    "depreciationAndAmortization": (
        ["DepreciationDepletionAndAmortization",
         "DepreciationAmortizationAndAccretionNet",
         "DepreciationAndAmortization"],
        "USD",
    ),
    "interestExpense": (["InterestExpense", "InterestExpenseDebt"], "USD"),
    "totalAssets": (["Assets"], "USD"),
    "totalLiabilities": (["Liabilities"], "USD"),
    "totalStockholdersEquity": (
        ["StockholdersEquity",
         "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
        "USD",
    ),
    "totalCurrentAssets": (["AssetsCurrent"], "USD"),
    "totalCurrentLiabilities": (["LiabilitiesCurrent"], "USD"),
    "cashAndShortTermInvestments": (
        ["CashCashEquivalentsAndShortTermInvestments",
         "CashAndCashEquivalentsAtCarryingValue"],
        "USD",
    ),
    "longTermDebt": (["LongTermDebtNoncurrent", "LongTermDebt"], "USD"),
    "shortTermDebt": (["LongTermDebtCurrent", "DebtCurrent", "ShortTermBorrowings"], "USD"),
    "operatingCashFlow": (
        ["NetCashProvidedByUsedInOperatingActivities",
         "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"],
        "USD",
    ),
    "capitalExpenditure": (
        ["PaymentsToAcquirePropertyPlantAndEquipment",
         "PaymentsToAcquireProductiveAssets"],
        "USD",
    ),
    "dividendsPaid": (["PaymentsOfDividendsCommonStock", "PaymentsOfDividends"], "USD"),
}

_DURATION = {  # conceitos "de período" (têm start+end); os restantes são snapshots
    "revenue", "grossProfit", "operatingIncome", "netIncome", "eps",
    "weightedAverageShsOutDil", "depreciationAndAmortization", "interestExpense",
    "operatingCashFlow", "capitalExpenditure", "dividendsPaid",
}


def _annual_map(
    node: dict, unit: str, is_duration: bool, prefer_original: bool = False
) -> dict[str, tuple[float, str]]:
    """{ano -> (valor, data_fim)}.

    `prefer_original=False`: valor do 10-K mais recente (capta reexpressões).
    `prefer_original=True` (nº de ações / EPS): valor do 10-K original do próprio
    ano — evita duplicar o ajuste de *stock splits* já aplicado em filings posteriores.
    """
    arr = (node.get("units") or {}).get(unit) or []
    by_end: dict[str, dict] = {}
    for x in arr:
        if x.get("form") not in ("10-K", "10-K/A"):
            continue
        end = x.get("end")
        if not end:
            continue
        if is_duration:
            start = x.get("start")
            if not start:
                continue
            if (date.fromisoformat(end) - date.fromisoformat(start)).days < 300:
                continue  # descarta trimestres
        prev = by_end.get(end)
        if prev is None:
            by_end[end] = x
            continue
        if prefer_original:
            end_year = int(end[:4])
            # menor |fy - ano| (o filing do próprio ano); desempate: filed mais antigo
            key_new = (abs((x.get("fy") or end_year) - end_year), x["filed"])
            key_old = (abs((prev.get("fy") or end_year) - end_year), prev["filed"])
            if key_new < key_old:
                by_end[end] = x
        elif x["filed"] > prev["filed"]:
            by_end[end] = x
    return {end[:4]: (by_end[end]["val"], end) for end in sorted(by_end)}


# nº de ações e EPS: usar o filing original (evita duplicar ajuste de splits)
_ORIGINAL = {"weightedAverageShsOutDil", "eps"}


def _series(facts: dict, concept: str) -> dict[str, tuple[float, str]]:
    gaap = facts.get("facts", {}).get("us-gaap", {})
    tags, unit = _CONCEPTS[concept]
    merged: dict[str, tuple[float, str]] = {}
    for tag in tags:
        node = gaap.get(tag)
        if not node:
            continue
        amap = _annual_map(
            node, unit, concept in _DURATION, prefer_original=concept in _ORIGINAL
        )
        for year, pair in amap.items():
            merged.setdefault(year, pair)  # 1.ª etiqueta com dados para esse ano ganha
    return merged


def _split_factor(splits: list[dict] | None, end_iso: str) -> float:
    """Fator para trazer nº de ações/EPS de `end_iso` para a base atual (pós-splits)."""
    f = 1.0
    for s in splits or []:
        d = str(s.get("date", ""))[:10]
        num, den = s.get("numerator"), s.get("denominator")
        if d and num and den and d > end_iso:
            f *= num / den
    return f


def deep_annual_df(
    cik: str, splits: list[dict] | None = None, max_years: int = 20
) -> pd.DataFrame:
    """DataFrame anual longo (ano no índice, ex.: '2011'..'2025').

    `splits` (da FMP) é usado para ajustar nº de ações e EPS à base atual —
    caso contrário os *stock splits* criam saltos artificiais nas séries longas.
    """
    facts = company_facts(cik)
    data = {c: _series(facts, c) for c in _CONCEPTS}
    years = sorted({y for s in data.values() for y in s})[-max_years:]
    df = pd.DataFrame(
        {c: [(data[c].get(y) or (None, None))[0] for y in years] for c in _CONCEPTS},
        index=years,
    )
    df.index.name = "Período"
    # data de fim de exercício por ano (para cruzar com cotações)
    ends: dict[str, str] = {}
    for c in ("netIncome", "revenue", "totalAssets"):
        for y, (_, end) in data.get(c, {}).items():
            ends.setdefault(y, end)
    df["periodEnd"] = [ends.get(y) or f"{y}-12-31" for y in years]

    # ajuste de stock splits: trazer nº de ações e EPS para a base atual
    if splits:
        fac = pd.Series(
            [_split_factor(splits, str(e)) for e in df["periodEnd"]], index=df.index
        )
        if "weightedAverageShsOutDil" in df.columns:
            df["weightedAverageShsOutDil"] = df["weightedAverageShsOutDil"] * fac
        if "eps" in df.columns:
            df["eps"] = df["eps"] / fac.replace(0, 1)

    # dívida total = curto + longo prazo
    df["totalDebt"] = df.get("shortTermDebt", 0).fillna(0) + df.get("longTermDebt", 0).fillna(0)
    df["totalDebt"] = df["totalDebt"].where(df["totalDebt"] > 0)
    # dívida líquida = dívida total - caixa
    df["netDebt"] = df["totalDebt"] - df.get("cashAndShortTermInvestments", 0).fillna(0)
    # EBITDA aproximado = resultado operacional + D&A
    df["ebitda"] = df["operatingIncome"] + df["depreciationAndAmortization"]
    return df
