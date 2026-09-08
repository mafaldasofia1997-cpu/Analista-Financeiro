"""Notas de análise por ação — modelo de análise fundamental do livro.

Guardadas em `app/notes.json` como {"AAPL": {"apresentacao": "...", ...}, ...}.
"""
from __future__ import annotations

from . import store

# (chave, título, ajuda) — segue o "Modelo de Análise Fundamental" (Investidor Prudente)
SECTIONS: list[tuple[str, str, str]] = [
    ("apresentacao", "2. Apresentação",
     "O que faz a empresa? Produtos/serviços, clientes, distribuição geográfica das "
     "vendas, setor e indústria."),
    ("historia", "2.1 História",
     "Marcos mais importantes desde a fundação, passando pelo IPO até à atualidade."),
    ("estrutura_acionista", "2.2 Estrutura acionista",
     "Quem controla a empresa? Fundadores, institucionais, free float."),
    ("gestao", "2.3 Equipa de gestão",
     "CEO e principais gestores; alinhamento com acionistas; histórico."),
    ("cotacao_lp", "3. Gráfico de cotações de longo prazo",
     "Tendência de longo prazo ascendente ou descendente? Quantos mais anos, melhor."),
    ("tendencias", "4. Tendências fundamentais — conclusões",
     "Resumo das 6 sobreposições (4.1 a 4.6): nº de ações e capitalização, vendas e "
     "P/S, EBITDA e EV/EBITDA, margens, resultado líquido e PER, dívida líquida e "
     "Net Debt/EBITDA."),
    ("riscos", "5. Fatores de risco",
     "Riscos 'especiais' desta empresa (secção Risk Factors do 10-K). Há algum risco "
     "que, só por si, invalida a oportunidade?"),
    ("mercado_alvo", "6. Dimensão do mercado-alvo e quota de mercado",
     "Qual o TAM? Que quota tem a empresa? Há espaço para crescer?"),
    ("concorrentes", "7. Comparação com concorrentes/congéneres",
     "Empresas da mesma indústria. Esta é a melhor forma de jogar esta tese, ou há "
     "concorrente mais atrativa/subavaliada?"),
    ("perspetivas", "8. Perspetivas",
     "O futuro será parecido com o passado? O que dizem os analistas especializados? "
     "O que já está descontado pelo mercado?"),
    ("tipo_play", "9. Tipo de play / oportunidade (Peter Lynch)",
     "Growth, Stalwart, Slow Grower, Dividend, Turnaround ou Asset Play — e porquê."),
    ("historia_investimento", "10. História de investimento",
     "Por extrapolação do passado, por evolução do passado, ou por rutura com o "
     "passado (catalisador). Qual o retorno médio anual esperado?"),
    ("conclusao", "Conclusão — comprar / manter / evitar",
     "A ação é, ou não é, para investir? Regra do livro: só é oportunidade se o ganho "
     "esperado for superior a 50%."),
]


def load_all() -> dict[str, dict]:
    data = store.read_json("notes.json", {})
    return data if isinstance(data, dict) else {}


def load(symbol: str) -> dict[str, str]:
    return load_all().get(symbol, {})


def save(symbol: str, data: dict[str, str]) -> None:
    alln = load_all()
    alln[symbol] = {k: v for k, v in data.items() if v and v.strip()}
    store.write_json("notes.json", alln)
