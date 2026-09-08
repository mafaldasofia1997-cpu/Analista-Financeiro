# Analista Financeiro

Plataforma local (Streamlit) para analisar as ações da tua carteira: seleciona uma
ação e vê, num só sítio, **notícias das últimas 48 horas**, as **demonstrações
financeiras reportadas** e **gráficos** desses dados com alternância **Anual /
Trimestral**.

Fonte de dados: [Financial Modeling Prep](https://site.financialmodelingprep.com/developer/docs)
(plano gratuito). As notícias usam a FMP e, em alternativa, o RSS do Google Notícias.

---

## 1. Pré-requisitos (uma vez)

### Instalar o Python 3.12

No PowerShell:

```powershell
winget install --id Python.Python.3.12 -e
```

Fecha e reabre o PowerShell e confirma:

```powershell
python --version
```

### Obter a API key da FMP

1. Cria conta gratuita em <https://site.financialmodelingprep.com/developer/docs>
2. Copia a tua API key.

---

## 2. Instalar a aplicação

No PowerShell, dentro da pasta `app`:

```powershell
cd "C:\Users\João Gomes\Desktop\Analista Financeiro\app"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> Se o `Activate.ps1` for bloqueado, corre uma vez:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### Configurar a API key

```powershell
copy .env.example .env
notepad .env
```

Preenche `FMP_API_KEY=a_tua_key` e grava.

---

## 3. Correr

```powershell
.\.venv\Scripts\Activate.ps1
streamlit run streamlit_app.py
```

Abre <http://localhost:8501>.

---

## Publicar online, grátis e privado (Streamlit Community Cloud)

O site fica num endereço `https://<nome>.streamlit.app`, **privado** (só os emails que
autorizares conseguem entrar) e **só o autor edita** (palavra-passe na sidebar). A
carteira e as notas passam a ser guardadas num **GitHub Gist secreto** (o disco do
Streamlit Cloud é volátil).

### A. Enviar o código para o GitHub

```powershell
winget install --id Git.Git -e      # se ainda não tiveres git
cd "C:\Users\João Gomes\Desktop\Analista Financeiro\app"
git init
git add .
git commit -m "Analista Financeiro"
git branch -M main
git remote add origin https://github.com/<user>/analista-financeiro.git
git push -u origin main
```

Cria primeiro o repositório em <https://github.com/new> (nome `analista-financeiro`,
**Private**, sem README/gitignore). O `.gitignore` já exclui `.env`, `.venv` e
`secrets.toml`.

### B. Criar o Gist (carteira + notas)

1. <https://gist.github.com> → ficheiro `portfolio.json` com o conteúdo do
   `portfolio.json` atual; **Add file** → `notes.json` com `{}`.
2. **Create secret gist**. Copia o **ID** do URL (`gist.github.com/<user>/<ID>`).

### C. Criar o token (deixa a app escrever no Gist)

<https://github.com/settings/tokens?type=beta> → **Generate new token** (fine-grained)
→ *Account permissions* → **Gists: Read and write** → gera e copia o `github_pat_...`.

### D. Publicar

1. <https://share.streamlit.io> → *Sign in with GitHub* → **Create app** → escolhe o
   repositório, branch `main`, ficheiro `streamlit_app.py`.
2. **Advanced settings → Secrets**, cola (com as tuas chaves):
   ```toml
   FMP_API_KEY   = "a_tua_key_FMP"
   ADMIN_PASSWORD = "uma_palavra_passe_forte"
   GIST_ID       = "id_do_gist"
   GITHUB_TOKEN  = "github_pat_..."
   ```
3. **Deploy** (~2–3 min).

### E. Tornar privado

No painel da app: **⋮ → Settings → Sharing** → desliga *Public* e adiciona os emails
autorizados. A partir daí o link só abre para esses emails (entram com Google).

### F. Editar a partir do site

Sidebar → **🔒 Modo edição** → introduz a `ADMIN_PASSWORD`. As alterações à carteira e
às notas ficam guardadas no Gist.

### Atualizar a app depois

```powershell
git add . ; git commit -m "alteração" ; git push
```

O Streamlit reconstrói sozinho.

---

## Utilização

- **Barra lateral** — escolhe uma ação da carteira, ou pesquisa por nome/ticker e
  carrega em **➕ Adicionar** para a guardar em `portfolio.json`.
- **Visão geral** — perfil da empresa, indicadores-chave e gráfico de preço a 2 anos.
- **Notícias (48 h)** — só notícias publicadas nas últimas 48 horas.
- **Financeiros** — escolhe **Anual/Trimestral** e a demonstração (Resultados,
  Balanço, Fluxos de caixa); tabela + gráficos das principais rubricas.
- **Tendências** — as 6 sobreposições da secção *4. Tendências Fundamentais* do
  modelo de César Borja (*Investidor Prudente*): métrica fundamental em barras + o
  respetivo múltiplo/rácio em linha, com eixos Y independentes por unidade (até 3)
  e a taxa média anual (CAGR) por baixo.
  - 4.1 Valor de Mercado, Enterprise Value, Nº de Ações e Cotação
  - 4.2 Vendas e Price/Sales
  - 4.3 EBITDA e EV/EBITDA
  - 4.4 Margens (bruta, EBITDA, operacional, líquida)
  - 4.5 Resultado Líquido e PER (PER = 0 quando o lucro é negativo)
  - 4.6 Dívida Líquida e Net Debt/EBITDA

  …ou **Personalizado**: escolhe da lista (`METRIC_CATALOG` em
  [financeiro/fundamentals.py](financeiro/fundamentals.py)). Em trimestral o plano
  gratuito não dá capitalização nem múltiplos de preço (P/S, PER, EV/EBITDA) — usa Anual.
- **Rácios & Qualidade** — todos os rácios do livro para o período mais recente
  (ROE, ROE operacional, ROIC, ROCE, margens, Net Debt/EBITDA, Dívida/Capital,
  Interest Coverage, Current Ratio, PER/PS/PB com mín-méd-máx histórico, PEG,
  SBC/Receita) com 🟢/🟡/🔴 face à referência do livro; CAGRs; e classificação
  automática no *tipo de play* de Peter Lynch.
- **Notas de análise** — o modelo de 10 pontos do livro (apresentação, história,
  estrutura acionista, gestão, riscos do 10-K, mercado-alvo, concorrentes,
  perspetivas, tipo de play, história de investimento, conclusão). Guardado por
  ticker em `notes.json`.

O tema visual (dark) está em [financeiro/ui.py](financeiro/ui.py) e em
`.streamlit/config.toml`. O modelo de análise foi extraído de *Análise Fundamental
de Ações* (Parte VI), de César Borja.

## Notas e limitações (plano gratuito da FMP)

- A app usa a API **`stable`** da FMP (`https://financialmodelingprep.com/stable`).
- Cobertura sobretudo de **ações dos EUA**; ~250 pedidos/dia (mitigado por cache).
  Símbolos não cobertos (ex.: BYD) mostram um erro claro em vez de rebentar.
- As demonstrações financeiras vêm limitadas a **5 períodos** (5 anos ou 5 trimestres).
  Os gráficos mostram esses 5 pontos; para histórico mais longo é preciso um plano pago.
- **Notícias das 48 h** — vêm de **Seeking Alpha** (feed direto por ticker) e de
  **Reuters, Yahoo Finance, Finviz e Trading Economics** através do Google Notícias com
  filtro `site:` + filtro de relevância pelo nome da empresa. Sem API key. A lista de
  domínios está em `NEWS_DOMAINS` em [financeiro/news.py](financeiro/news.py) e é fácil
  de editar.
- `.env` nunca deve ser partilhado nem submetido a controlo de versões.
