"""Dossiê automático — preenche o modelo de "Apresentação/Análise" do livro
(César Borja) com os dados disponíveis (FMP + SEC EDGAR).

Cada função devolve (título, markdown). Onde não há dados gratuitos estruturados
(quota de mercado, top-10 acionistas), fica um apontador em vez de campo vazio.
"""
from __future__ import annotations

import pandas as pd

from . import edgar, fmp_client, fundamentals
from .fmp_client import FMPError


def _n(v, suf="", pre="", dec=2):
    if not isinstance(v, (int, float)) or v != v:
        return "—"
    return f"{pre}{v:,.{dec}f}{suf}"


def _bn(v):
    """Formata em mil milhões (mM). Ex.: 4_094_870_374_731 -> '4 094,9 mM'."""
    if not isinstance(v, (int, float)) or v != v or v == 0:
        return "—"
    if abs(v) < 1e6:
        return f"{v:,.0f}"
    return f"{v / 1e9:,.1f} mM"


def _try(fn, *a, **k):
    try:
        return fn(*a, **k)
    except FMPError:
        return []
    except Exception:
        return []


def _apresentacao(profile: dict) -> tuple[str, str]:
    linhas = [
        f"**Setor:** {profile.get('sector') or '—'} · **Indústria:** {profile.get('industry') or '—'}",
        f"**Sede:** {profile.get('country') or '—'} · **Bolsa:** {profile.get('exchange') or '—'} "
        f"· **Moeda:** {profile.get('currency') or '—'}",
        f"**Website:** {profile.get('website') or '—'} · **Colaboradores:** "
        f"{_n(_to_int(profile.get('fullTimeEmployees')), dec=0)}",
        "",
        (profile.get("description") or "Sem descrição disponível.").strip(),
    ]
    return "2. Apresentação", "\n\n".join(linhas)


def _to_int(v):
    try:
        return int(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _segmentos(symbol: str) -> tuple[str, str]:
    prod = _try(fmp_client.get_product_segments, symbol)
    geo = _try(fmp_client.get_geo_segments, symbol)

    def fmt(rows, titulo):
        if not rows:
            return f"**{titulo}:** sem dados."
        r = rows[0]
        data = r.get("data") or {}
        total = sum(v for v in data.values() if isinstance(v, (int, float))) or 1
        itens = sorted(data.items(), key=lambda kv: -(kv[1] or 0))
        linhas = [f"- {k}: {_bn(v)} ({v / total * 100:,.0f}%)" for k, v in itens]
        return f"**{titulo}** (FY{r.get('fiscalYear')}):\n" + "\n".join(linhas)

    return "2. Vendas por segmento e geografia", fmt(prod, "Por produto/serviço") + "\n\n" + fmt(
        geo, "Por geografia"
    )


def _historia(profile: dict, deep_df: pd.DataFrame | None) -> tuple[str, str]:
    ipo = profile.get("ipoDate")
    txt = f"**IPO:** {ipo or '—'}."
    if deep_df is not None and len(deep_df):
        txt += f" Histórico fundamental disponível desde **{deep_df.index[0]}** (SEC EDGAR)."
    txt += (
        "\n\nMarcos da empresa (fundação, produtos-chave, aquisições): ver o site de "
        "*Investor Relations* e a secção *Item 1 — Business* do 10-K."
    )
    return "2.1 História", txt


def _estrutura_acionista(symbol: str, cik: str | None) -> tuple[str, str]:
    fl = _try(fmp_client.get_shares_float, symbol)
    txt = ""
    if fl:
        f = fl[0]
        txt = (
            f"**Free float:** {_n(f.get('freeFloat'), '%', dec=1)} · "
            f"**Ações em circulação:** {_bn(f.get('outstandingShares'))} · "
            f"**Ações no free float:** {_bn(f.get('floatShares'))}\n\n"
        )
    ptr = "Top-10 acionistas e posições dos fundadores: consultar os *13F* e o "
    if cik:
        ptr += f"[*proxy statement* (DEF 14A) da empresa](https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=DEF+14A)."
    else:
        ptr += "*proxy statement* (DEF 14A) da empresa."
    return "2.2 Estrutura acionista", txt + ptr


def _gestao(symbol: str, profile: dict) -> tuple[str, str]:
    execs = _try(fmp_client.get_key_executives, symbol)
    chave = ("chief executive", " ceo", "chairman", "chief financial", " cfo",
             "chief operating", "president", "founder")
    sel = [
        e for e in execs
        if any(k in f" {(e.get('title') or '').lower()}" for k in chave)
    ] or execs[:5]
    linhas = []
    ceo_nome = (profile.get("ceo") or "").strip()
    if ceo_nome and not any(ceo_nome.lower() in (e.get("name") or "").lower() for e in sel):
        linhas.append(f"- **CEO** — {ceo_nome}")
    linhas += [
        f"- **{e.get('title')}** — {e.get('name')}"
        + (f" (nascido {e.get('yearBorn')})" if e.get("yearBorn") else "")
        for e in sel
    ]
    if not linhas:
        linhas = [f"- CEO: {ceo_nome or '—'}"]
    linhas.append(
        "\n*Track record* de cada gestor: ver biografias no *proxy statement* e notícias."
    )
    return "2.3 Equipa de gestão", "\n".join(linhas)


def _riscos(cik: str | None) -> tuple[str, str]:
    filing = edgar.latest_10k(cik) if cik else None
    if filing:
        txt = (
            f"Ler a secção **Item 1A — Risk Factors** do 10-K mais recente "
            f"(arquivado em {filing['date']}):\n\n[{filing['url']}]({filing['url']})\n\n"
            "Anotar apenas os riscos *específicos* desta empresa (os genéricos aplicam-se "
            "a qualquer ação). Atenção especial a menções de *material weakness* no "
            "controlo interno sobre o reporte financeiro."
        )
    else:
        txt = "10-K não localizado na SEC (empresa não-EUA?). Procurar o relatório anual no site da empresa."
    return "5. Fatores de risco", txt


def _mercado_alvo(profile: dict, symbol: str) -> tuple[str, str]:
    peers = _try(fmp_client.get_peers, symbol)
    nomes = ", ".join(p.get("symbol", "") for p in peers[:8]) or "—"
    txt = (
        "Dimensão do mercado-alvo (TAM) e quota de mercado **não estão disponíveis "
        "em dados gratuitos estruturados** — exigem pesquisa qualitativa.\n\n"
        f"Pontos de partida: relatórios de mercado do setor *{profile.get('industry') or profile.get('sector')}*, "
        f"a secção *Item 1 — Business* do 10-K, e a comparação de receitas com os pares "
        f"({nomes}) para estimar a quota relativa."
    )
    return "6. Dimensão do mercado-alvo e quota de mercado", txt


def _concorrentes(symbol: str) -> tuple[str, str]:
    peers = _try(fmp_client.get_peers, symbol)
    if not peers:
        return "7. Comparação com concorrentes", "Sem lista de pares disponível."
    linhas = ["| Empresa | Capitalização |", "|---|---|"]
    for p in peers[:8]:
        linhas.append(f"| {p.get('symbol')} — {p.get('companyName') or ''} | {_bn(p.get('mktCap'))} |")
    linhas.append(
        "\nComparar margens, crescimento e múltiplos (abas **Tendências**/**Rácios**) "
        "com estes pares para ver se esta é a melhor forma de jogar a tese."
    )
    return "7. Comparação com concorrentes", "\n".join(linhas)


def _perspetivas(symbol: str) -> tuple[str, str]:
    est = _try(fmp_client.get_analyst_estimates, symbol, "annual", 5)
    pts = _try(fmp_client.get_price_target_summary, symbol)
    grades = _try(fmp_client.get_grades, symbol)
    partes = []
    if est:
        linhas = ["**Estimativas dos analistas (média):**", "", "| Ano | Receita | EPS |", "|---|---|---|"]
        for e in est[:4]:
            linhas.append(
                f"| {str(e.get('date',''))[:4]} | {_bn(e.get('revenueAvg'))} | {_n(e.get('epsAvg'))} |"
            )
        partes.append("\n".join(linhas))
    if pts:
        p = pts[0]
        partes.append(
            f"**Price targets (últ. trimestre):** média {_n(p.get('lastQuarterAvgPriceTarget'))} "
            f"de {p.get('lastQuarterCount')} analistas."
        )
    if grades:
        recentes = "; ".join(
            f"{g.get('gradingCompany')}: {g.get('newGrade')}" for g in grades[:5]
        )
        partes.append(f"**Ratings recentes:** {recentes}")
    partes.append(
        "*Nota:* o livro avisa que *price targets* a 12 meses são pouco fiáveis; usar "
        "as estimativas apenas como referência para a **História de Investimento**."
    )
    return "8. Perspetivas", "\n\n".join(partes) if partes else "Sem dados de analistas."


def _tipo_play(mdf: pd.DataFrame | None) -> tuple[str, str]:
    if mdf is None or mdf.empty:
        return "9. Tipo de play (Peter Lynch)", "Sem dados suficientes."
    play, motivos = fundamentals.classify_play(mdf)
    return "9. Tipo de play (Peter Lynch)", f"**{play}**\n\n" + "\n".join(f"- {m}" for m in motivos)


def _historia_investimento(mdf: pd.DataFrame | None) -> tuple[str, str]:
    if mdf is None or mdf.empty:
        return "10. História de investimento", "Sem dados suficientes."
    horizonte = 5
    linhas = [
        "**Por extrapolação do passado** — taxas médias anuais (CAGR) do histórico "
        f"disponível, projetadas a {horizonte} anos:",
        "",
        "| Métrica | CAGR | Projeção +5 anos |",
        "|---|---|---|",
    ]
    for label, col in [
        ("Receita", "revenue"),
        ("Resultado líquido", "netIncome"),
        ("Free cash flow", "freeCashFlow"),
        ("EPS", "eps"),
        ("Capitalização de mercado", "marketCap"),
    ]:
        if col not in mdf.columns:
            continue
        g = fundamentals.cagr(mdf[col])
        s = mdf[col].dropna()
        proj = s.iloc[-1] * ((1 + g) ** horizonte) if (g is not None and len(s)) else None
        linhas.append(
            f"| {label} | {'—' if g is None else f'{g * 100:+.1f}%/ano'} | "
            f"{'—' if proj is None else _bn(proj) if abs(proj) > 1e6 else _n(proj)} |"
        )
    gm = fundamentals.cagr(mdf["marketCap"]) if "marketCap" in mdf.columns else None
    if gm is not None:
        linhas.append(
            f"\nRetorno médio anual implícito (via capitalização): **{gm * 100:+.1f}%/ano**. "
            "Ajustar para *evolução do passado* (múltiplos a normalizar) ou *rutura* "
            "(catalisador que muda as tendências)."
        )
    return "10. História de investimento", "\n".join(linhas)


def _conclusao(mdf: pd.DataFrame | None) -> tuple[str, str]:
    if mdf is None or mdf.empty:
        return "Conclusão", "Sem dados suficientes."
    pontos = []
    last = mdf.iloc[-1]
    roe = last.get("roec")
    roic = last.get("returnOnInvestedCapital")
    if isinstance(roe, (int, float)) and roe == roe:
        pontos.append(f"Qualidade: ROE {roe * 100:.0f}%" + (f", ROIC ~{roic * 100:.0f}%" if isinstance(roic, (int, float)) and roic == roic else ""))
    for col, nome in [("perAdj", "PER"), ("priceToSalesRatio", "P/S"), ("evToEBITDA", "EV/EBITDA")]:
        s = mdf[col].dropna() if col in mdf.columns else pd.Series(dtype="float64")
        if len(s) >= 4:
            v = s.iloc[-1]
            pct = (s < v).mean() * 100
            pos = "acima" if pct > 60 else "abaixo" if pct < 40 else "em linha com"
            pontos.append(f"{nome} {v:,.1f}× — {pos} da média histórica (percentil {pct:.0f})")
    play, _ = fundamentals.classify_play(mdf)
    pontos.append(f"Tipo de *play*: {play}")
    pontos.append(
        "**Regra do livro:** só é oportunidade se o ganho esperado for **> 50%**. "
        "Cruzar esta síntese com os fatores de risco e a comparação com concorrentes."
    )
    return "Conclusão — comprar / manter / evitar", "\n".join(f"- {p}" for p in pontos)


def build_dossier(
    symbol: str,
    profile: dict,
    cik: str | None,
    deep_df: pd.DataFrame | None,
    mdf: pd.DataFrame | None,
) -> list[tuple[str, str]]:
    return [
        _apresentacao(profile),
        _segmentos(symbol),
        _historia(profile, deep_df),
        _estrutura_acionista(symbol, cik),
        _gestao(symbol, profile),
        _riscos(cik),
        _mercado_alvo(profile, symbol),
        _concorrentes(symbol),
        _perspetivas(symbol),
        _tipo_play(mdf),
        _historia_investimento(mdf),
        _conclusao(mdf),
    ]
