"""Tema visual (dark, moderno) injetado por CSS no topo da app."""
from __future__ import annotations

import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;700;800&display=swap');

:root {
  --verde: #16C784;
  --verde-soft: rgba(22, 199, 132, 0.12);
  --fundo: #0D1117;
  --card: #161B22;
  --borda: #232A33;
  --txt: #E6EDF3;
  --txt-dim: #8B949E;
}

html, body, [class*="css"], .stMarkdown, .stApp {
  font-family: 'Manrope', system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
}

.stApp { background: var(--fundo); }

/* Cabeçalho / títulos */
h1, h2, h3 { font-weight: 800 !important; letter-spacing: -0.02em; }
h1 { font-size: 2.1rem !important; }

/* Barra lateral */
section[data-testid="stSidebar"] {
  background: #0A0D12;
  border-right: 1px solid var(--borda);
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 { color: var(--txt); }

/* Cartões de métrica */
div[data-testid="stMetric"] {
  background: var(--card);
  border: 1px solid var(--borda);
  border-radius: 14px;
  padding: 14px 16px;
}
div[data-testid="stMetric"] label p { color: var(--txt-dim) !important; font-weight: 600; }
div[data-testid="stMetricValue"] { font-weight: 800; }

/* Separadores (tabs) */
.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid var(--borda); }
.stTabs [data-baseweb="tab"] {
  background: transparent;
  border-radius: 10px 10px 0 0;
  padding: 10px 16px;
  font-weight: 700;
  color: var(--txt-dim);
}
.stTabs [aria-selected="true"] {
  background: var(--verde-soft);
  color: var(--verde) !important;
  box-shadow: inset 0 -2px 0 var(--verde);
}

/* Botões */
.stButton > button {
  border-radius: 10px;
  border: 1px solid var(--borda);
  font-weight: 700;
}
.stButton > button:hover { border-color: var(--verde); color: var(--verde); }

/* Radios / multiselect / inputs mais compactos */
div[data-baseweb="select"] > div, .stTextInput input {
  border-radius: 10px !important;
  background: var(--card) !important;
}

/* Tabelas */
div[data-testid="stDataFrame"] { border: 1px solid var(--borda); border-radius: 12px; }

/* Cartão de notícia */
.news-card {
  background: var(--card);
  border: 1px solid var(--borda);
  border-left: 3px solid var(--verde);
  border-radius: 12px;
  padding: 14px 16px;
  margin-bottom: 10px;
}
.news-card a { color: var(--txt); text-decoration: none; font-weight: 700; font-size: 1.02rem; }
.news-card a:hover { color: var(--verde); }
.news-card .meta { color: var(--txt-dim); font-size: 0.82rem; margin-top: 4px; }

/* Faixa do título da empresa */
.hero {
  background: linear-gradient(135deg, rgba(22,199,132,0.10), rgba(22,199,132,0.02));
  border: 1px solid var(--borda);
  border-radius: 16px;
  padding: 18px 22px;
  margin-bottom: 8px;
}
.hero .name { font-size: 1.7rem; font-weight: 800; letter-spacing: -0.02em; }
.hero .sub { color: var(--txt-dim); font-size: 0.9rem; margin-top: 2px; }

footer, #MainMenu { visibility: hidden; }
.block-container { padding-top: 2.2rem; }
</style>
"""


def inject_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def hero(name: str, subtitle: str) -> None:
    sub = f'<div class="sub">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f'<div class="hero"><div class="name">{name}</div>{sub}</div>',
        unsafe_allow_html=True,
    )


def news_card(title: str, url: str, meta: str, snippet: str = "") -> None:
    body = f'<div style="color:var(--txt-dim);font-size:0.9rem;margin-top:6px">{snippet}…</div>' if snippet else ""
    st.markdown(
        f'<div class="news-card"><a href="{url}" target="_blank">{title}</a>'
        f'<div class="meta">{meta}</div>{body}</div>',
        unsafe_allow_html=True,
    )
