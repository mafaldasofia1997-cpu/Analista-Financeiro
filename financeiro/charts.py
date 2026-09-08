"""Figuras Plotly para os dados financeiros reportados."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

PALETTE = ["#2563eb", "#16a34a", "#dc2626", "#9333ea", "#ea580c", "#0891b2"]


def _layout(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(
        title=title,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=52, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        height=360,
        hovermode="x unified",
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.06)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.06)")
    return fig


def bars(
    df: pd.DataFrame, columns: list[str], title: str, currency: bool = True
) -> go.Figure:
    fig = go.Figure()
    for i, col in enumerate(columns):
        if col not in df.columns:
            continue
        y = df[col] / 1e9 if currency else df[col]
        fig.add_bar(name=col, x=df.index, y=y, marker_color=PALETTE[i % len(PALETTE)])
    fig.update_layout(barmode="group")
    if currency:
        fig.update_yaxes(title_text="mil milhões $")
    return _layout(fig, title)


def lines(
    df: pd.DataFrame, columns: list[str], title: str, percent: bool = False
) -> go.Figure:
    fig = go.Figure()
    for i, col in enumerate(columns):
        if col not in df.columns:
            continue
        fig.add_scatter(
            name=col,
            x=df.index,
            y=df[col],
            mode="lines+markers",
            line=dict(color=PALETTE[i % len(PALETTE)], width=2),
        )
    if percent:
        fig.update_yaxes(ticksuffix="%")
    return _layout(fig, title)


def combo(
    bar_df: pd.DataFrame,
    bar_col: str,
    line_df: pd.DataFrame,
    line_col: str,
    title: str,
) -> go.Figure:
    fig = go.Figure()
    if bar_col in bar_df.columns:
        fig.add_bar(
            name=bar_col,
            x=bar_df.index,
            y=bar_df[bar_col] / 1e9,
            marker_color=PALETTE[0],
        )
    if line_col in line_df.columns:
        fig.add_scatter(
            name=line_col,
            x=line_df.index,
            y=line_df[line_col],
            mode="lines+markers",
            yaxis="y2",
            line=dict(color=PALETTE[2], width=2),
        )
    fig.update_layout(
        yaxis=dict(title="mil milhões $"),
        yaxis2=dict(title="%", overlaying="y", side="right", ticksuffix="%"),
    )
    return _layout(fig, title)


def overlay(series: list[dict], title: str) -> go.Figure:
    """Sobrepõe várias séries com eixos Y por unidade.

    Cada item de `series`: {name, x, values, kind ('bar'|'line'), unit, unit_label}.
    Unidades: 'bn' e 'cnt' são divididas por 1e9; 'pct' é multiplicada por 100.
    Até 3 eixos Y distintos (um por unidade, pela ordem de aparência).
    """
    units: list[str] = []
    for s in series:
        if s["unit"] not in units:
            units.append(s["unit"])
    units = units[:3]
    axis_of = {u: i + 1 for i, u in enumerate(units)}

    def scale(unit: str, vals):
        v = pd.Series(vals, dtype="float64")
        if unit in ("bn", "cnt"):
            return v / 1e9
        if unit == "pct":
            return v * 100
        return v

    fig = go.Figure()
    for i, s in enumerate(series):
        if s["unit"] not in axis_of:
            continue
        ax = axis_of[s["unit"]]
        y = scale(s["unit"], s["values"])
        yaxis = "y" if ax == 1 else f"y{ax}"
        color = PALETTE[i % len(PALETTE)]
        if s["kind"] == "bar":
            fig.add_bar(name=s["name"], x=s["x"], y=y, yaxis=yaxis,
                        marker_color=color, opacity=0.55)
        else:
            fig.add_scatter(name=s["name"], x=s["x"], y=y, yaxis=yaxis,
                            mode="lines+markers", line=dict(color=color, width=2.5))

    suffix = {"bn": "", "cnt": "", "price": "$", "x": "×", "pct": "%"}
    three = len(units) == 3
    layout: dict = {
        "title": dict(text=title, y=0.98, font=dict(size=14)),
        "template": "plotly_dark",
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "margin": dict(l=10, r=10, t=40, b=64),
        "height": 440,
        "hovermode": "x unified",
        "legend": dict(orientation="h", yanchor="top", y=-0.14, x=0),
        "barmode": "group",
    }
    for u, ax in axis_of.items():
        label = next(s["unit_label"] for s in series if s["unit"] == u)
        key = "yaxis" if ax == 1 else f"yaxis{ax}"
        cfg = dict(title=label, showgrid=(ax == 1),
                   gridcolor="rgba(255,255,255,0.06)",
                   ticksuffix=suffix.get(u, ""))
        if ax >= 2:
            cfg.update(overlaying="y", side="right")
        if ax == 3:
            cfg.update(anchor="free", position=1.0)
        layout[key] = cfg
    if three:
        layout["xaxis"] = dict(domain=[0.0, 0.86])

    fig.update_layout(**layout)
    return fig


def price(hist: list[dict], title: str) -> go.Figure:
    fig = go.Figure()
    df = pd.DataFrame(hist)
    if not df.empty and {"date", "close"}.issubset(df.columns):
        df = df.sort_values("date")
        fig.add_scatter(
            x=df["date"],
            y=df["close"],
            mode="lines",
            line=dict(color=PALETTE[0], width=1.6),
            name="Fecho",
        )
    return _layout(fig, title)
