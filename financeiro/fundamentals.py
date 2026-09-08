"""Normalização das demonstrações financeiras reportadas para DataFrames.

O índice de cada DataFrame é o período em ordem cronológica (ex.: ``FY2025`` para
anual, ``2026-Q2`` para trimestral), pronto a alimentar tabelas e gráficos.
"""
from __future__ import annotations

import pandas as pd

# (campo na FMP, rótulo em PT)
RESULTADOS = [
    ("revenue", "Receita"),
    ("grossProfit", "Lucro bruto"),
    ("operatingIncome", "Resultado operacional"),
    ("netIncome", "Resultado líquido"),
    ("ebitda", "EBITDA"),
    ("eps", "EPS ($)"),
]
BALANCO = [
    ("totalAssets", "Ativo total"),
    ("totalLiabilities", "Passivo total"),
    ("totalStockholdersEquity", "Capital próprio"),
    ("cashAndShortTermInvestments", "Caixa e investimentos CP"),
    ("totalDebt", "Dívida total"),
]
FLUXOS = [
    ("operatingCashFlow", "Fluxo de caixa operacional"),
    ("capitalExpenditure", "CapEx"),
    ("freeCashFlow", "Free cash flow"),
    ("netDividendsPaid", "Dividendos pagos"),
    ("netChangeInCash", "Variação de caixa"),
]

SPECS: dict[str, list[tuple[str, str]]] = {
    "resultados": RESULTADOS,
    "balanco": BALANCO,
    "fluxos": FLUXOS,
}

# Rótulos que NÃO são valores monetários (não devem ser escalados para mil milhões)
NAO_MONETARIOS = {"EPS ($)"}


def _period_label(row: dict) -> str:
    year = str(
        row.get("fiscalYear")
        or row.get("calendarYear")
        or (row.get("date", "") or "")[:4]
    )
    per = (row.get("period") or "").upper()
    if per and per != "FY":
        return f"{year}-{per}"
    return f"FY{year}"


def build_statement_df(rows: list[dict], statement_type: str) -> pd.DataFrame:
    """Constrói um DataFrame (períodos no índice, rubricas nas colunas)."""
    spec = SPECS[statement_type]
    rows = sorted(rows, key=lambda r: r.get("date", ""))
    periods = [_period_label(r) for r in rows]
    data = {label: [r.get(key) for r in rows] for key, label in spec}
    df = pd.DataFrame(data, index=periods)
    df.index.name = "Período"
    return df


def build_margins_df(income_rows: list[dict]) -> pd.DataFrame:
    """Margens em % a partir da demonstração de resultados."""
    rows = sorted(income_rows, key=lambda r: r.get("date", ""))
    idx = [_period_label(r) for r in rows]

    def pct(numerador: str) -> list[float | None]:
        out: list[float | None] = []
        for r in rows:
            n, d = r.get(numerador), r.get("revenue")
            out.append((n / d * 100) if (n is not None and d) else None)
        return out

    df = pd.DataFrame(
        {
            "Margem bruta %": pct("grossProfit"),
            "Margem operacional %": pct("operatingIncome"),
            "Margem líquida %": pct("netIncome"),
        },
        index=idx,
    )
    df.index.name = "Período"
    return df


# --------------------------------------------------------------------------- #
# Tendências fundamentais — segundo o modelo de César Borja (Investidor Prudente)
# --------------------------------------------------------------------------- #

# rótulo apresentável -> (coluna interna, unidade, tipo de traço)
#   unidades: "bn"=mil milhões $ | "cnt"=contagem (ações) | "price"=$ | "x"=múltiplo | "pct"=%
METRIC_CATALOG: dict[str, tuple[str, str, str]] = {
    "Capitalização de mercado": ("marketCap", "bn", "bar"),
    "Enterprise value (EV)": ("enterpriseValue", "bn", "bar"),
    "Receita": ("revenue", "bn", "bar"),
    "EBITDA": ("ebitda", "bn", "bar"),
    "Resultado operacional (EBIT)": ("operatingIncome", "bn", "bar"),
    "Resultado líquido": ("netIncome", "bn", "bar"),
    "Free cash flow": ("freeCashFlow", "bn", "bar"),
    "Dívida líquida": ("netDebt", "bn", "bar"),
    "Capital próprio": ("totalStockholdersEquity", "bn", "bar"),
    "Nº de ações (diluído)": ("weightedAverageShsOutDil", "cnt", "line"),
    "Cotação implícita": ("impliedPrice", "price", "line"),
    "EPS": ("eps", "price", "line"),
    "PER": ("perAdj", "x", "line"),
    "Price / Sales": ("priceToSalesRatio", "x", "line"),
    "Price / Book": ("priceToBookRatio", "x", "line"),
    "EV / EBITDA": ("evToEBITDA", "x", "line"),
    "EV / Vendas": ("evToSales", "x", "line"),
    "PEG": ("priceToEarningsGrowthRatio", "x", "line"),
    "Net Debt / EBITDA": ("netDebtToEBITDAc", "x", "line"),
    "Dívida / Capital próprio": ("debtToEquityc", "x", "line"),
    "Current ratio": ("currentRatioc", "x", "line"),
    "Interest coverage": ("interestCoveragec", "x", "line"),
    "Margem bruta": ("grossProfitMargin", "pct", "line"),
    "Margem EBITDA": ("ebitdaMargin", "pct", "line"),
    "Margem operacional": ("operatingProfitMargin", "pct", "line"),
    "Margem líquida": ("netProfitMargin", "pct", "line"),
    "Margem FCF": ("fcfMargin", "pct", "line"),
    "ROE": ("roec", "pct", "line"),
    "ROE operacional": ("roeOp", "pct", "line"),
    "ROIC": ("returnOnInvestedCapital", "pct", "line"),
    "ROCE": ("returnOnCapitalEmployed", "pct", "line"),
    "Dividend yield": ("dividendYield", "pct", "line"),
}

# As 6 sobreposições da secção "4. Tendências Fundamentais" do livro
PRESETS: dict[str, list[str]] = {
    "4.1 — Valor de Mercado, Nº de Ações e Cotação": [
        "Capitalização de mercado",
        "Enterprise value (EV)",
        "Nº de ações (diluído)",
        "Cotação implícita",
    ],
    "4.2 — Vendas e Price/Sales": ["Receita", "Price / Sales"],
    "4.3 — EBITDA e EV/EBITDA": ["EBITDA", "EV / EBITDA"],
    "4.4 — Margens (bruta, EBITDA, operacional, líquida)": [
        "Margem bruta",
        "Margem EBITDA",
        "Margem operacional",
        "Margem líquida",
    ],
    "4.5 — Resultado Líquido e PER": ["Resultado líquido", "PER"],
    "4.6 — Dívida Líquida e Net Debt/EBITDA": [
        "Dívida líquida",
        "Net Debt / EBITDA",
    ],
}

UNIT_LABEL = {
    "bn": "mil milhões $",
    "cnt": "mil milhões (ações)",
    "price": "$",
    "x": "múltiplo (×)",
    "pct": "%",
}


def _index_by_period(rows: list[dict]) -> dict[str, dict]:
    return {_period_label(r): r for r in rows}


def _coalesce(*series: pd.Series | None) -> pd.Series | None:
    out = None
    for s in series:
        if s is None:
            continue
        out = s.copy() if out is None else out.fillna(s)
    return out


def metrics_df(
    income_rows: list[dict],
    ratios_rows: list[dict],
    keymetrics_rows: list[dict],
    cashflow_rows: list[dict],
    balance_rows: list[dict] | None = None,
) -> pd.DataFrame:
    """Junta métricas de várias demonstrações num só DataFrame (período no índice).

    `key-metrics` e `ratios` só existem em Anual no plano gratuito da FMP; por isso
    as margens e vários rácios são recalculados a partir de resultados/balanço,
    para funcionarem também em Trimestral.
    """
    inc = _index_by_period(income_rows)
    rat = _index_by_period(ratios_rows)
    km = _index_by_period(keymetrics_rows)
    cf = _index_by_period(cashflow_rows)
    bs = _index_by_period(balance_rows or [])

    periods = sorted(
        set(inc) | set(rat) | set(km) | set(cf) | set(bs),
        key=lambda p: (p[2:] if p.startswith("FY") else p),
    )

    def val(store: dict, period: str, field: str):
        return (store.get(period) or {}).get(field)

    cols = {
        "marketCap": km,
        "enterpriseValue": km,
        "evToEBITDA": km,
        "evToSales": km,
        "returnOnEquity": km,
        "returnOnInvestedCapital": km,
        "returnOnCapitalEmployed": km,
        "netDebtToEBITDA": km,
        "currentRatio": km,
        "revenue": inc,
        "ebitda": inc,
        "ebit": inc,
        "operatingIncome": inc,
        "grossProfit": inc,
        "netIncome": inc,
        "eps": inc,
        "interestExpense": inc,
        "weightedAverageShsOutDil": inc,
        "priceToEarningsRatio": rat,
        "priceToSalesRatio": rat,
        "priceToBookRatio": rat,
        "priceToEarningsGrowthRatio": rat,
        "debtToEquityRatio": rat,
        "interestCoverageRatio": rat,
        "dividendYield": rat,
        "freeCashFlow": cf,
        "operatingCashFlow": cf,
        "capitalExpenditure": cf,
        "stockBasedCompensation": cf,
        "totalStockholdersEquity": bs,
        "totalDebt": bs,
        "netDebt": bs,
        "totalCurrentAssets": bs,
        "totalCurrentLiabilities": bs,
        "totalAssets": bs,
    }
    frame = {f: [val(s, p, f) for p in periods] for f, s in cols.items()}
    df = pd.DataFrame(frame, index=periods).apply(pd.to_numeric, errors="coerce")
    df.index.name = "Período"

    def col(name: str) -> pd.Series | None:
        return df[name] if name in df.columns else None

    def safe(s: pd.Series | None) -> pd.Series | None:
        return None if s is None else s.replace(0, pd.NA)

    rev = safe(col("revenue"))
    equity = safe(col("totalStockholdersEquity"))
    ebitda = safe(col("ebitda"))

    # margens (%) — sempre a partir de resultados
    if rev is not None:
        for src, dst in (
            ("grossProfit", "grossProfitMargin"),
            ("operatingIncome", "operatingProfitMargin"),
            ("ebitda", "ebitdaMargin"),
            ("netIncome", "netProfitMargin"),
            ("freeCashFlow", "fcfMargin"),
        ):
            if src in df.columns:
                df[dst] = df[src] / rev

    # cotação implícita = capitalização / nº de ações diluído
    shares = safe(col("weightedAverageShsOutDil"))
    if shares is not None and col("marketCap") is not None:
        df["impliedPrice"] = col("marketCap") / shares

    # PER ajustado: 0 quando o resultado líquido é <= 0 (regra do livro)
    per = col("priceToEarningsRatio")
    ni = col("netIncome")
    if per is not None:
        df["perAdj"] = per.where(ni > 0, 0) if ni is not None else per
    elif col("marketCap") is not None and ni is not None:
        df["perAdj"] = (col("marketCap") / safe(ni)).where(ni > 0, 0)

    # rácios com fallback calculado (funcionam em Trimestral)
    df["netDebtToEBITDAc"] = _coalesce(
        col("netDebtToEBITDA"),
        (col("netDebt") / ebitda) if ebitda is not None else None,
    )
    df["debtToEquityc"] = _coalesce(
        col("debtToEquityRatio"),
        (col("totalDebt") / equity) if equity is not None else None,
    )
    df["currentRatioc"] = _coalesce(
        col("currentRatio"),
        (col("totalCurrentAssets") / safe(col("totalCurrentLiabilities")))
        if col("totalCurrentLiabilities") is not None
        else None,
    )
    df["roec"] = _coalesce(
        col("returnOnEquity"),
        (col("netIncome") / equity) if equity is not None else None,
    )
    df["roeOp"] = (
        (col("operatingIncome") / equity)
        if equity is not None
        else pd.Series(float("nan"), index=df.index)
    )
    ie = safe(col("interestExpense"))
    icov = _coalesce(
        col("interestCoverageRatio"),
        (col("operatingIncome") / ie.abs()) if ie is not None else None,
    )
    # juros ~0 (ex.: Apple) -> rácio sem significado, deixar vazio em vez de 0
    df["interestCoveragec"] = icov.where(icov > 0) if icov is not None else icov
    if "stockBasedCompensation" in df.columns and rev is not None:
        df["sbcToRevenue"] = df["stockBasedCompensation"].abs() / rev

    return df


def _close_near(price_rows: list[dict], iso_date: str) -> float | None:
    """Fecho do último dia de negociação <= iso_date (rows: {date, close|price})."""
    if not price_rows or not iso_date:
        return None
    pts = sorted(
        (
            (r.get("date", "")[:10], r.get("close", r.get("price")))
            for r in price_rows
            if r.get("close") is not None or r.get("price") is not None
        )
    )
    best = None
    for d, p in pts:
        if d <= iso_date:
            best = p
        else:
            break
    return best if best is not None else (pts[0][1] if pts else None)


def deep_annual_metrics(edgar_df: pd.DataFrame, price_rows: list[dict]) -> pd.DataFrame:
    """Converte o histórico longo da SEC EDGAR + cotações num DataFrame anual
    compatível com METRIC_CATALOG / RATIO_ROWS / PRESETS."""
    df = edgar_df.copy()

    def c(name: str) -> pd.Series:
        return df[name] if name in df.columns else pd.Series(float("nan"), index=df.index)

    def safe(s: pd.Series) -> pd.Series:
        return s.replace(0, pd.NA)

    rev, equity, ebitda = safe(c("revenue")), safe(c("totalStockholdersEquity")), safe(c("ebitda"))
    ni = c("netIncome")

    # capitalização histórica = cotação no fim do exercício × nº de ações diluído
    if "periodEnd" in df.columns:
        closes = pd.Series(
            [_close_near(price_rows, str(e)) for e in df["periodEnd"]],
            index=df.index, dtype="float64",
        )
        df["impliedPrice"] = closes
        df["marketCap"] = closes * c("weightedAverageShsOutDil")
        df["enterpriseValue"] = df["marketCap"] + c("netDebt")

    mcap = safe(c("marketCap"))
    df["freeCashFlow"] = c("operatingCashFlow") - c("capitalExpenditure").abs()

    for src, dst in (
        ("grossProfit", "grossProfitMargin"),
        ("operatingIncome", "operatingProfitMargin"),
        ("ebitda", "ebitdaMargin"),
        ("netIncome", "netProfitMargin"),
        ("freeCashFlow", "fcfMargin"),
    ):
        df[dst] = c(src) / rev

    df["perAdj"] = (c("marketCap") / safe(ni)).where(ni > 0, 0)
    df["priceToSalesRatio"] = c("marketCap") / rev
    df["priceToBookRatio"] = c("marketCap") / equity
    df["evToEBITDA"] = c("enterpriseValue") / ebitda
    df["evToSales"] = c("enterpriseValue") / rev
    df["netDebtToEBITDAc"] = c("netDebt") / ebitda
    df["debtToEquityc"] = c("totalDebt") / equity
    df["currentRatioc"] = c("totalCurrentAssets") / safe(c("totalCurrentLiabilities"))
    df["roec"] = c("netIncome") / equity
    df["roeOp"] = c("operatingIncome") / equity
    # ROCE = EBIT / Capital Employed (Ativo - Passivo Corrente) — método 1 do livro
    df["returnOnCapitalEmployed"] = c("operatingIncome") / safe(
        c("totalAssets") - c("totalCurrentLiabilities")
    )
    # ROIC ≈ NOPAT / (Capital Próprio + Dívida Líquida), NOPAT ≈ EBIT × 0,79
    df["returnOnInvestedCapital"] = (c("operatingIncome") * 0.79) / safe(
        c("totalStockholdersEquity") + c("netDebt")
    )
    ie = safe(c("interestExpense"))
    icov = c("operatingIncome") / ie.abs()
    df["interestCoveragec"] = icov.where(icov > 0)
    df["dividendYield"] = c("dividendsPaid").abs() / mcap
    df["priceToEarningsGrowthRatio"] = pd.Series(float("nan"), index=df.index)
    return df


def cagr(series: pd.Series) -> float | None:
    """Taxa média anual de crescimento entre o 1.º e o último valor não nulo.

    Só é calculável quando ambos os extremos são positivos (o livro usa esta
    fórmula para nº de ações, vendas, EBITDA, resultado líquido, valor de mercado).
    """
    s = series.dropna()
    if len(s) < 2:
        return None
    first, last, n = float(s.iloc[0]), float(s.iloc[-1]), len(s) - 1
    if first <= 0 or last <= 0:
        return None
    return (last / first) ** (1 / n) - 1


# Linhas do painel "Rácios & Qualidade" — (rótulo, coluna, formato, teste, nota do livro)
#   formato: "pct" | "x" | "bn"
#   teste(v) -> "ok" | "warn" | "bad" | None
def _t(ok, warn, *, invert=False, net_cash_ok=False):
    def test(v):
        if v is None or v != v:  # NaN
            return None
        if net_cash_ok and v < 0:
            return "ok"
        if invert:
            if v <= ok:
                return "ok"
            if v <= warn:
                return "warn"
            return "bad"
        if v >= ok:
            return "ok"
        if v >= warn:
            return "warn"
        return "bad"
    return test


RATIO_ROWS: list[tuple[str, str, str, object, str]] = [
    ("ROE", "roec", "pct", _t(0.10, 0.05),
     "O livro aprecia ROE > 10%."),
    ("ROE operacional (EBIT / Capital Próprio)", "roeOp", "pct", _t(0.20, 0.10),
     "O livro aprecia ROE operacional consistentemente > 20%."),
    ("ROIC", "returnOnInvestedCapital", "pct", _t(0.20, 0.10),
     "ROIC > 20% de forma consistente = negócio de muita qualidade (Munger)."),
    ("ROCE", "returnOnCapitalEmployed", "pct", _t(0.15, 0.08),
     "EBIT / Capital Employed."),
    ("Margem bruta", "grossProfitMargin", "pct", None,
     "Comparar com empresas da mesma indústria."),
    ("Margem EBITDA", "ebitdaMargin", "pct", None, "EBITDA / Vendas."),
    ("Margem operacional", "operatingProfitMargin", "pct", None, "EBIT / Vendas."),
    ("Margem líquida", "netProfitMargin", "pct", None, "Resultado Líquido / Vendas."),
    ("Margem FCF", "fcfMargin", "pct", _t(0.05, 0.0),
     "Free Cash Flow / Vendas. Deve ser positiva."),
    ("Net Debt / EBITDA", "netDebtToEBITDAc", "x", _t(3.0, 4.0, invert=True, net_cash_ok=True),
     "O livro quer < 3. Negativo = posição de Net Cash (ótimo)."),
    ("Dívida / Capital próprio", "debtToEquityc", "x", _t(0.5, 1.0, invert=True),
     "O livro considera saudável a longo prazo se < 0,5."),
    ("Interest coverage (EBIT / Juros)", "interestCoveragec", "x", _t(8.0, 3.0),
     "Quanto mais alto, melhor."),
    ("Current ratio", "currentRatioc", "x", _t(1.5, 1.0),
     "Ativo Corrente / Passivo Corrente."),
    ("PER (ajustado)", "perAdj", "x", None,
     "Comparar com a própria média histórica (ver abaixo)."),
    ("Price / Sales", "priceToSalesRatio", "x", None,
     "Comparar com a própria média histórica."),
    ("Price / Book", "priceToBookRatio", "x", None, "Relevante para Asset Plays."),
    ("PEG", "priceToEarningsGrowthRatio", "x", _t(1.0, 2.0, invert=True),
     "PER / crescimento do EPS. < 1 costuma indicar subavaliação."),
    ("EV / EBITDA", "evToEBITDA", "x", None, "Comparar com a própria média histórica."),
    ("Dividend yield", "dividendYield", "pct", None, "Relevante para Dividend Plays."),
    ("SBC / Receita", "sbcToRevenue", "pct", _t(0.04, 0.08, invert=True),
     "As 10 maiores empresas pagam ~4% da receita em stock-based compensation."),
]

# Séries para as quais faz sentido mostrar a taxa média anual (CAGR)
CAGR_ROWS: list[tuple[str, str]] = [
    ("Nº de ações (diluído)", "weightedAverageShsOutDil"),
    ("Receita", "revenue"),
    ("EBITDA", "ebitda"),
    ("Resultado líquido", "netIncome"),
    ("Free cash flow", "freeCashFlow"),
    ("Capitalização de mercado", "marketCap"),
    ("EPS", "eps"),
]


def classify_play(df: pd.DataFrame) -> tuple[str, list[str]]:
    """Classifica a ação num dos 6 tipos de 'play' do Peter Lynch (via livro)."""
    notas: list[str] = []
    rev_g = cagr(df["revenue"]) if "revenue" in df else None
    eps_g = cagr(df["eps"]) if "eps" in df else None
    growth = max([g for g in (rev_g, eps_g) if g is not None], default=None)

    dy = None
    if "dividendYield" in df and df["dividendYield"].notna().any():
        dy = float(df["dividendYield"].dropna().iloc[-1])
    pb = None
    if "priceToBookRatio" in df and df["priceToBookRatio"].notna().any():
        pb = float(df["priceToBookRatio"].dropna().iloc[-1])
    drawdown = None
    if "impliedPrice" in df and df["impliedPrice"].notna().sum() >= 2:
        p = df["impliedPrice"].dropna()
        drawdown = 1 - float(p.iloc[-1]) / float(p.max())

    if growth is not None:
        notas.append(f"Crescimento (máx. de vendas/EPS): {growth * 100:.1f}%/ano")
    if dy is not None:
        notas.append(f"Dividend yield: {dy * 100:.2f}%")
    if pb is not None:
        notas.append(f"Price/Book: {pb:.2f}")
    if drawdown is not None:
        notas.append(f"Queda desde o máximo (cotação implícita): {drawdown * 100:.0f}%")

    if drawdown is not None and drawdown > 0.8:
        return "Turnaround Play", notas + ["Caiu mais de 80% desde o máximo."]
    if pb is not None and pb < 1:
        return "Asset Play", notas + ["Price/Book < 1: ativos podem valer mais do que a cotação."]
    if dy is not None and dy > 0.04:
        return "Dividend Play", notas + ["Dividend yield elevado (> 4%)."]
    if growth is not None:
        if growth >= 0.15:
            return "Growth Play", notas + ["Crescimento de 15%–25% ou superior."]
        if growth >= 0.06:
            return "Stalwart", notas + ["Crescimento moderado (6%–12%)."]
        return "Slow Grower", notas + ["Crescimento lento (até ~6%)."]
    return "Indeterminado", notas + ["Dados insuficientes para classificar."]

