"""Analista Financeiro — plataforma local de análise de ações.

Seleciona uma ação da carteira e vê, num só sítio:
  • notícias das últimas 48 horas
  • demonstrações financeiras reportadas (resultados / balanço / fluxos de caixa)
  • gráficos desses dados, com alternância Anual / Trimestral
"""
from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import streamlit as st

from financeiro import (
    access,
    charts,
    company,
    edgar,
    fmp_client,
    fundamentals,
    notes,
    store,
    ui,
)
from financeiro.config import get_api_key
from financeiro.fmp_client import FMPError
from financeiro.news import FONTES_LABEL as NEWS_FONTES, get_recent_news

st.set_page_config(page_title="Analista Financeiro", page_icon="📈", layout="wide")
ui.inject_theme()

PERIODOS = ["Anual", "Trimestral"]
_PERIODO_API = {"Anual": "annual", "Trimestral": "quarter"}

DEFAULT_PORTFOLIO = [
    {"symbol": "AAPL", "name": "Apple Inc."},
    {"symbol": "AMZN", "name": "Amazon.com, Inc."},
    {"symbol": "NVDA", "name": "NVIDIA Corporation"},
    {"symbol": "TSLA", "name": "Tesla, Inc."},
    {"symbol": "LLY", "name": "Eli Lilly and Company"},
    {"symbol": "PG", "name": "The Procter & Gamble Company"},
    {"symbol": "KO", "name": "The Coca-Cola Company"},
    {"symbol": "O", "name": "Realty Income Corporation"},
    {"symbol": "BYDDY", "name": "BYD Company Limited (ADR)"},
]


def load_portfolio() -> list[dict]:
    data = store.read_json("portfolio.json", DEFAULT_PORTFOLIO)
    items = [d for d in data if isinstance(d, dict) and d.get("symbol")]
    return items or DEFAULT_PORTFOLIO


def save_portfolio(items: list[dict]) -> None:
    store.write_json("portfolio.json", items)


# --------------------------------------------------------------------------- #
# Gate: API key
# --------------------------------------------------------------------------- #
if not get_api_key():
    st.title("📈 Analista Financeiro")
    st.error(
        "**Falta a API key da Financial Modeling Prep.**\n\n"
        "- Local: copia `.env.example` para `.env` e preenche `FMP_API_KEY=...`\n"
        "- Streamlit Cloud: define `FMP_API_KEY` em *Settings → Secrets*\n\n"
        "Conta gratuita: https://site.financialmodelingprep.com/developer/docs"
    )
    st.stop()

portfolio = load_portfolio()
is_editor = access.editor_gate()

# --------------------------------------------------------------------------- #
# Sidebar — carteira + pesquisa
# --------------------------------------------------------------------------- #
st.sidebar.title("A minha carteira")

if "symbol" not in st.session_state:
    st.session_state.symbol = portfolio[0]["symbol"] if portfolio else "AAPL"

if portfolio:
    labels = {f'{p["name"]} — {p["symbol"]}': p["symbol"] for p in portfolio}
    current = next(
        (lbl for lbl, sym in labels.items() if sym == st.session_state.symbol), None
    )
    chosen = st.sidebar.radio(
        "Seleciona a ação",
        list(labels),
        index=list(labels).index(current) if current else 0,
    )
    st.session_state.symbol = labels[chosen]
else:
    st.sidebar.info("Carteira vazia — usa a pesquisa abaixo para adicionar ações.")

st.sidebar.divider()
st.sidebar.subheader("Procurar / adicionar ação")
query = st.sidebar.text_input("Nome ou ticker", key="search_query", placeholder="ex.: MSFT")
if query:
    try:
        results = fmp_client.search_symbol(query)
    except FMPError as exc:
        results = []
        st.sidebar.error(str(exc))
    if results:
        options = {
            f'{r.get("symbol")} — {r.get("name")} '
            f'({r.get("exchange") or "?"})': r
            for r in results
        }
        pick = st.sidebar.selectbox("Resultados", list(options))
        if is_editor:
            col_a, col_b = st.sidebar.columns(2)
            ver = col_a.button("Ver agora", width="stretch")
            add = col_b.button("➕ Adicionar", width="stretch")
        else:
            ver = st.sidebar.button("Ver agora", width="stretch")
            add = False
        if ver:
            st.session_state.symbol = options[pick]["symbol"]
            st.rerun()
        if add:
            sym = options[pick]["symbol"]
            if not any(p["symbol"] == sym for p in portfolio):
                portfolio.append(
                    {"symbol": sym, "name": options[pick].get("name") or sym}
                )
                save_portfolio(portfolio)
                st.session_state.symbol = sym
                st.sidebar.success(f"{sym} adicionado à carteira.")
                st.rerun()
    elif query.strip():
        st.sidebar.caption("Sem resultados.")

symbol: str = st.session_state.symbol

# --------------------------------------------------------------------------- #
# Dados base (perfil + cotação)
# --------------------------------------------------------------------------- #
try:
    profile = fmp_client.get_profile(symbol)
    quote = fmp_client.get_quote(symbol)
except FMPError as exc:
    st.title("📈 Analista Financeiro")
    st.error(f"Não foi possível carregar **{symbol}**: {exc}")
    st.stop()

company_name = profile.get("companyName") or symbol
currency = profile.get("currency") or "USD"

meta = " · ".join(
    x
    for x in (
        profile.get("exchange"),
        profile.get("sector"),
        profile.get("industry"),
    )
    if x
)
ui.hero(f"{company_name} ({symbol})", meta)

def _money(v: object) -> str:
    if not isinstance(v, (int, float)) or not v:
        return "—"
    if abs(v) >= 1e12:
        return f"{v / 1e12:.2f} T"
    if abs(v) >= 1e9:
        return f"{v / 1e9:.1f} B"
    return f"{v / 1e6:.0f} M"


c1, c2, c3, c4 = st.columns(4)
price_now = quote.get("price")
change_pct = quote.get("changePercentage")
c1.metric(
    f"Preço ({currency})",
    f"{price_now:,.2f}" if price_now is not None else "—",
    f"{change_pct:+.2f}%" if change_pct is not None else None,
)
c2.metric("Capitalização", _money(quote.get("marketCap")))
c3.metric("Máx 52 sem.", f"{quote.get('yearHigh'):,.2f}" if quote.get("yearHigh") else "—")
c4.metric("Mín 52 sem.", f"{quote.get('yearLow'):,.2f}" if quote.get("yearLow") else "—")

tab_overview, tab_news, tab_fin, tab_trends, tab_ratios, tab_notes = st.tabs(
    [
        "📋 Visão geral",
        "📰 Notícias (48 h)",
        "📊 Financeiros",
        "📈 Tendências",
        "🧮 Rácios & Qualidade",
        "📝 Notas de análise",
    ]
)

# --------------------------------------------------------------------------- #
# Visão geral
# --------------------------------------------------------------------------- #
with tab_overview:
    st.subheader("Sobre a empresa")
    st.write(profile.get("description") or "Sem descrição disponível.")

    left, right = st.columns(2)
    with left:
        st.markdown("**Indicadores-chave (último ano reportado)**")
        try:
            ratios = fmp_client.get_ratios(symbol, "annual")
        except FMPError as exc:
            ratios = []
            st.caption(f"Sem métricas: {exc}")
        if ratios:
            latest = ratios[0]

            def _num(v: object, pct: bool = False, dec: int = 2) -> str:
                if isinstance(v, (int, float)):
                    return f"{v * 100:,.{dec}f}%" if pct else f"{v:,.{dec}f}"
                return "—"

            table = {
                "P/E": _num(latest.get("priceToEarningsRatio")),
                "P/B": _num(latest.get("priceToBookRatio")),
                "Dívida / Capital próprio": _num(latest.get("debtToEquityRatio")),
                "Margem líquida": _num(latest.get("netProfitMargin"), pct=True),
                "Dividend yield": _num(latest.get("dividendYield"), pct=True),
                "Receita / ação": _num(latest.get("revenuePerShare")),
            }
            st.table(pd.Series(table, name="Valor").to_frame())
    with right:
        try:
            hist = fmp_client.get_price_history(symbol)
            st.plotly_chart(
                charts.price(hist, "Preço de fecho — 2 anos"),
                width="stretch",
            )
        except FMPError as exc:
            st.caption(f"Sem histórico de preço: {exc}")

# --------------------------------------------------------------------------- #
# Notícias (últimas 48 h)
# --------------------------------------------------------------------------- #
with tab_news:
    with st.spinner("A procurar notícias das últimas 48 horas..."):
        news = get_recent_news(symbol, company_name, hours=48)

    st.subheader(f"{len(news)} notícia(s) nas últimas 48 horas")
    st.caption(f"Fontes: {NEWS_FONTES}.")
    if not news:
        st.info(
            "Não foram encontradas notícias nas últimas 48 horas nestas fontes."
        )
    else:
        now = datetime.now(timezone.utc)
        for item in news:
            hrs = (now - item.published_dt).total_seconds() / 3600
            when = f"há {int(hrs)} h" if hrs >= 1 else "há menos de 1 h"
            extra = "" if item.provider == item.source else f" · via {item.provider}"
            ui.news_card(
                item.title, item.url, f"{item.source} · {when}{extra}", item.snippet
            )

# --------------------------------------------------------------------------- #
# Financeiros — tabela + gráficos por demonstração
# --------------------------------------------------------------------------- #
with tab_fin:
    top_l, top_r = st.columns(2)
    periodo = top_l.radio("Periodicidade", PERIODOS, horizontal=True, key="fin_periodo")
    demo = top_r.radio(
        "Demonstração",
        ["Resultados", "Balanço", "Fluxos de caixa"],
        horizontal=True,
        key="fin_demo",
    )
    api_period = _PERIODO_API[periodo]
    demo_key = {"Resultados": "resultados", "Balanço": "balanco", "Fluxos de caixa": "fluxos"}[demo]
    fetch = {
        "resultados": fmp_client.get_income_statement,
        "balanco": fmp_client.get_balance_sheet,
        "fluxos": fmp_client.get_cash_flow,
    }[demo_key]

    rows: list[dict] = []
    try:
        rows = fetch(symbol, api_period)
    except FMPError as exc:
        st.error(str(exc))

    if not rows:
        st.info("Sem dados para esta demonstração / periodicidade.")
    else:
        df = fundamentals.build_statement_df(rows, demo_key)
        recent = df.iloc[::-1]  # mais recente primeiro, para leitura
        st.dataframe(
            recent.T.style.format("{:,.0f}", na_rep="—"),
            width="stretch",
        )
        st.caption(
            "Valores em moeda de reporte (exceto EPS, por ação). "
            "O plano gratuito da FMP devolve no máximo 5 períodos."
        )

        monetarias = [c for c in df.columns if c not in fundamentals.NAO_MONETARIOS]
        g1, g2 = st.columns(2)
        with g1:
            if monetarias:
                st.plotly_chart(
                    charts.bars(df, monetarias[:3], f"{demo} — principais rubricas"),
                    width="stretch",
                )
        with g2:
            if "EPS ($)" in df.columns:
                st.plotly_chart(
                    charts.bars(df, ["EPS ($)"], "EPS", currency=False),
                    width="stretch",
                )
            elif len(monetarias) > 3:
                st.plotly_chart(
                    charts.bars(df, monetarias[3:], f"{demo} — outras rubricas"),
                    width="stretch",
                )

# --------------------------------------------------------------------------- #
# Helper partilhado — junta as métricas (FMP; ou SEC EDGAR para o histórico longo)
# --------------------------------------------------------------------------- #
def load_metrics(sym: str, period: str, cik: str | None = None, years: int = 5) -> pd.DataFrame:
    # Histórico anual longo via SEC EDGAR (empresas dos EUA)
    if period == "annual" and cik and years > 5:
        try:
            splits = fmp_client.get_splits(sym)
            deep = edgar.deep_annual_df(cik, splits, max_years=years)
            if len(deep) > 5:
                prices = fmp_client.get_price_history_deep(sym, years=years + 2)
                mdf = fundamentals.deep_annual_metrics(deep, prices)
                mdf.attrs["fonte"] = f"SEC EDGAR — {len(mdf)} anos (ajustado a splits)"
                return mdf
        except Exception:
            pass  # cai para a FMP

    def g(fn):
        try:
            return fn(sym, period)
        except FMPError:
            return []

    mdf = fundamentals.metrics_df(
        g(fmp_client.get_income_statement),
        g(fmp_client.get_ratios),
        g(fmp_client.get_key_metrics),
        g(fmp_client.get_cash_flow),
        g(fmp_client.get_balance_sheet),
    )
    mdf.attrs["fonte"] = f"FMP — {len(mdf)} períodos (plano gratuito: máx. 5)"
    return mdf


_FLAG = {"ok": "🟢", "warn": "🟡", "bad": "🔴", None: "⚪"}


def _fmt_val(v: object, kind: str) -> str:
    if not isinstance(v, (int, float)) or v != v:
        return "—"
    if kind == "pct":
        return f"{v * 100:,.1f}%"
    if kind == "x":
        return f"{v:,.2f}×"
    if kind == "bn":
        return f"{v / 1e9:,.2f} B"
    return f"{v:,.2f}"


# --------------------------------------------------------------------------- #
# Tendências fundamentais — as 6 sobreposições do modelo do livro (secção 4)
# --------------------------------------------------------------------------- #
with tab_trends:
    st.subheader("Tendências fundamentais")
    st.caption(
        "As 6 sobreposições da secção *4. Tendências Fundamentais* do modelo de "
        "César Borja (Investidor Prudente): métrica fundamental em barras + o "
        "respetivo múltiplo/rácio em linha."
    )
    col_p, col_c = st.columns([1, 2])
    periodo_c = col_p.radio("Periodicidade", PERIODOS, horizontal=True, key="cmp_periodo")
    api_period_c = _PERIODO_API[periodo_c]
    preset = col_c.selectbox(
        "Sobreposição", list(fundamentals.PRESETS) + ["Personalizado"]
    )

    cik = profile.get("cik")
    anos_t = 5
    if api_period_c == "annual" and cik:
        anos_t = st.slider("Nº de anos", 5, 20, 15, key="trend_years")

    if preset == "Personalizado":
        metrics = st.multiselect(
            "Métricas (agrupadas por unidade — até 3 eixos)",
            list(fundamentals.METRIC_CATALOG),
            default=["Receita", "Margem líquida"],
        )
    else:
        metrics = fundamentals.PRESETS[preset]
        st.caption("Séries: " + " · ".join(metrics))

    mdf = load_metrics(symbol, api_period_c, cik, anos_t)

    if api_period_c == "quarter":
        st.caption(
            "ℹ️ Em trimestral o plano gratuito não dá capitalização nem múltiplos "
            "(P/S, PER, EV/EBITDA). Sobreposições 4.2, 4.3 e 4.5 precisam de **Anual**."
        )

    if mdf.empty:
        st.info("Sem dados financeiros.")
    elif not metrics:
        st.info("Escolhe pelo menos uma métrica.")
    else:
        st.caption(f"Fonte: {mdf.attrs.get('fonte', '—')}.")
        series: list[dict] = []
        faltam: list[str] = []
        for label in metrics:
            col, unit, kind = fundamentals.METRIC_CATALOG[label]
            if col not in mdf.columns or mdf[col].dropna().empty:
                faltam.append(label)
                continue
            series.append(
                {
                    "name": label,
                    "x": list(mdf.index),
                    "values": list(mdf[col]),
                    "kind": kind,
                    "unit": unit,
                    "unit_label": fundamentals.UNIT_LABEL[unit],
                }
            )
        if faltam:
            st.warning("Sem dados nesta periodicidade para: " + ", ".join(faltam))
        if len({s["unit"] for s in series}) > 3:
            st.caption("⚠️ Mais de 3 unidades — só as 3 primeiras têm eixo próprio.")

        if series:
            titulo = preset if preset != "Personalizado" else "métricas selecionadas"
            st.plotly_chart(
                charts.overlay(series, f"{company_name} — {titulo}"), width="stretch"
            )
            # taxas médias anuais (CAGR) das séries fundamentais em barras
            cagrs = []
            for s in series:
                if s["kind"] == "bar":
                    g = fundamentals.cagr(mdf[fundamentals.METRIC_CATALOG[s["name"]][0]])
                    if g is not None:
                        cagrs.append(f"**{s['name']}**: {g * 100:+.1f}%/ano")
            if cagrs:
                st.markdown("Taxa média anual (do 1.º ao último período): " + " · ".join(cagrs))
            with st.expander("Ver dados"):
                cols_show = [
                    fundamentals.METRIC_CATALOG[m][0]
                    for m in metrics
                    if fundamentals.METRIC_CATALOG[m][0] in mdf.columns
                ]
                st.dataframe(
                    mdf[cols_show].iloc[::-1].style.format("{:,.2f}", na_rep="—"),
                    width="stretch",
                )

# --------------------------------------------------------------------------- #
# Rácios & Qualidade — todos os rácios do livro + CAGRs + tipo de "play"
# --------------------------------------------------------------------------- #
with tab_ratios:
    st.subheader("Rácios & Qualidade")
    rp = st.radio("Periodicidade", PERIODOS, horizontal=True, key="rat_periodo")
    rcik = profile.get("cik")
    ranos = 5
    if _PERIODO_API[rp] == "annual" and rcik:
        ranos = st.slider("Nº de anos", 5, 20, 15, key="rat_years")
    rmdf = load_metrics(symbol, _PERIODO_API[rp], rcik, ranos)

    if rmdf.empty:
        st.info("Sem dados financeiros.")
    else:
        last = rmdf.index[-1]
        st.caption(
            f"Fonte: {rmdf.attrs.get('fonte', '—')}. Valores do período mais recente: **{last}**."
        )

        rows = []
        for label, col, kind, test, nota in fundamentals.RATIO_ROWS:
            if col not in rmdf.columns:
                continue
            serie = rmdf[col].dropna()
            if serie.empty:
                continue
            v = serie.iloc[-1]
            flag = _FLAG[test(v)] if test else ""
            extra = ""
            if col in ("perAdj", "priceToSalesRatio", "evToEBITDA") and len(serie) >= 2:
                extra = (
                    f"mín {serie.min():.1f}× · méd {serie.mean():.1f}× · máx {serie.max():.1f}×"
                )
            rows.append(
                {
                    "": flag,
                    "Rácio": label,
                    last: _fmt_val(v, kind),
                    "Histórico": extra,
                    "Referência do livro": nota,
                }
            )
        if rows:
            st.dataframe(pd.DataFrame(rows).set_index("Rácio"), width="stretch")
            st.caption(
                "🟢 dentro da referência do livro · 🟡 aceitável · 🔴 fora · "
                "⚪ sem referência fixa (comparar com histórico / indústria)"
            )
        else:
            st.info("Sem rácios disponíveis nesta periodicidade (tenta **Anual**).")

        st.markdown("#### Taxas médias anuais (CAGR)")
        window = ""
        if len(rmdf) >= 2:
            window = f" · {rmdf.index[0]} → {rmdf.index[-1]}"
        crows = []
        for label, col in fundamentals.CAGR_ROWS:
            if col in rmdf.columns:
                g = fundamentals.cagr(rmdf[col])
                crows.append({"Métrica": label, "CAGR": "—" if g is None else f"{g * 100:+.1f}%/ano"})
        if crows:
            st.caption(f"Janela: {len(rmdf)} períodos{window}")
            st.dataframe(pd.DataFrame(crows).set_index("Métrica"), width="stretch")

        st.markdown("#### Tipo de *play* (Peter Lynch)")
        play, motivos = fundamentals.classify_play(rmdf)
        st.markdown(f"### {play}")
        for m in motivos:
            st.markdown(f"- {m}")
        st.caption(
            "Classificação automática a partir dos dados. Confirma na aba **Notas** "
            "(ponto 9) com o teu julgamento."
        )

# --------------------------------------------------------------------------- #
# Dossiê de análise — preenchido automaticamente (modelo do livro)
# --------------------------------------------------------------------------- #
with tab_notes:
    st.subheader(f"Dossiê de análise — {company_name}")
    st.caption(
        "Preenchido automaticamente segundo o *Modelo de Análise Fundamental* de "
        "César Borja (*Investidor Prudente*), com dados da FMP e da SEC EDGAR. "
        "Os pontos quantitativos (cotação de longo prazo e tendências fundamentais) "
        "estão nas abas **Tendências** e **Rácios**."
    )
    _cik = profile.get("cik")
    with st.spinner("A montar o dossiê..."):
        _deep = None
        if _cik:
            try:
                _deep = edgar.deep_annual_df(_cik, fmp_client.get_splits(symbol), max_years=20)
            except Exception:
                _deep = None
        _dmdf = load_metrics(symbol, "annual", _cik, 20)
        secoes = company.build_dossier(symbol, profile, _cik, _deep, _dmdf)

    for titulo, corpo in secoes:
        st.markdown(f"#### {titulo}")
        st.markdown(corpo)
        st.divider()

    st.markdown("#### Notas adicionais")
    saved = notes.load(symbol)
    if is_editor:
        txt = st.text_area(
            "As tuas observações (por cima do dossiê automático)",
            value=saved,
            height=160,
        )
        if st.button("💾 Guardar notas"):
            notes.save(symbol, txt)
            st.success("Guardado.")
    elif saved:
        st.write(saved)
    else:
        st.caption("Sem notas adicionais.")
