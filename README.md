# ProInvestAI

**Plataforma de inteligência financeira para investidores brasileiros e gestores de RPPS.**

Combina otimização matemática (Markowitz), análise atuarial (ALM) e IA generativa para montar carteiras profissionais com produtos reais do mercado brasileiro — e estudos de ALM para Regimes Próprios de Previdência Social com aderência à CMN 5.272/2025.

---

## O que o sistema faz

### Módulo PF — Investidor Pessoa Física

| Funcionalidade | Detalhe |
|---|---|
| **Suitability Quiz** | 28 perguntas em 7 seções, nível CEA/ANBIMA, classifica o perfil (Conservador, Moderado, Arrojado) |
| **Montagem de Carteira** | Otimização Markowitz (max Sharpe) com 15 produtos reais do mercado brasileiro |
| **Dados Macro em Tempo Real** | Selic, IPCA e CDI projetados via BCB Focus API (Olinda) |
| **Projeções Forward** | Ano a ano usando a trajetória do Focus, com IR regressivo e custódia B3 |
| **Simulação Monte Carlo** | 5.000 cenários estocásticos para projetar patrimônio futuro |
| **Gap Analysis** | Comparação entre carteira atual do usuário e a recomendada |
| **Parecer com IA** | Narração personalizada via GPT-4o-mini em português |
| **Stress Test** | Backtest contra crises históricas (2008, COVID-19, etc.) |

### Módulo RPPS — Regimes Próprios de Previdência Social

| Funcionalidade | Detalhe |
|---|---|
| **Parser Atuarial** | Leitura de fluxos do CadPrev (CSV) com estrutura receitas × despesas |
| **Taxa de Equilíbrio** | Cálculo da taxa mínima de retorno real para solvência (método de Brent) |
| **ALM Markowitz** | Fronteira eficiente com 10 portfólios, índices ANBIMA (CDI, IRF-M, IMA-B, IMA Geral) |
| **Enquadramento Regulatório** | Constraints por artigo da CMN 5.272/2025 (Art. 7 a 12) e níveis de governança (PI 2026) |
| **NTN-B Liability Matching** | Casamento de duração entre NTN-Bs e passivo atuarial |
| **Monte Carlo de Solvência** | 1.000 cenários para probabilidade de insolvência ao longo do horizonte atuarial |
| **Métricas Institucionais** | VaR, Sharpe, Treynor, Drawdown, Tracking Error, Information Ratio por fundo |
| **Relatório em PDF** | Geração automática do relatório de risco e carteira recomendada |

---

## Catálogo de Ativos (Módulo PF)

| Produto | Retorno Base | IR | Liquidez | Proteção |
|---|---|---|---|---|
| Tesouro Selic 2031 | Selic + 0,08% | Regressivo | D+1 | Governo Federal |
| CDB Liquidez Diária | 100% CDI | Regressivo | D+0 | FGC R$250k |
| LCI/LCA | 93% CDI | **Isento** | D+90 | FGC R$250k |
| Tesouro IPCA+ 2032 | IPCA + 7,61% | Regressivo | D+1 | Governo Federal |
| Tesouro IPCA+ JS 2037 | IPCA + 7,38% | Regressivo | D+1 (cupons) | Governo Federal |
| Debênture Incentivada | IPCA + 7,0% | **Isento** | D+30 | Risco de crédito |
| Tesouro Prefixado 2028 | ~98% CDI | Regressivo | D+1 | Governo Federal |
| CDB Prefixado | ~110% CDI | Regressivo | D+360 | FGC R$250k |
| FII (IFIX) | IPCA + 5,5% | **Isento** (dividendos) | D+3 | Mercado |
| ETF Ibovespa (BOVA11) | IPCA + 8,5% | 15% | D+3 | Mercado |
| ETF Small Caps (SMAL11) | IPCA + 10% | 15% | D+3 | Mercado |
| Ações Dividendos (IDIV) | IPCA + 9% | 15% | D+3 | Mercado |
| ETF S&P 500 (IVVB11) | ~10% USD | 15% | D+3 | Mercado |
| Previdência PGBL RF | ~95% CDI | Tabela regressiva | D+60 | — |
| Bitcoin via ETF (HASH11) | — | 15% | D+3 | Mercado |

### Constraints por Perfil

| Perfil | Máx. Renda Variável | Reserva de Emergência | Mín. Liquidez | Internacional |
|---|---|---|---|---|
| Conservador | 5% | 12 meses | 35% | 0% |
| Moderado | 20% | 6 meses | 20% | 10% |
| Arrojado | 40% | 3 meses | 10% | 20% |

---

## Índices RPPS (Módulo ALM — CMN 5.272/2025)

```
CDI · IRF-M 1 · IRF-M · IMA-B 5 · IMA-B · IMA-B 5+
IMA Geral Ex-C · IDkA IPCA 2A · IDkA Pré 2A · IRF-M 1+
Carteira Títulos Públicos ALM · Fundos Crédito Privado
Fundos Multimercados · Ibovespa · IFIX
```

Cada índice carrega: segmento, artigo regulatório, modelo de projeção (ETTJ ANBIMA, histórico 60m, spread CDI, cupom ponderado), peso mínimo/máximo e flag de iliquidez (posições de vértice travadas).

---

## Arquitetura

O projeto segue **Clean Architecture** com separação estrita de camadas:

```
proinvestai/
├── app/
│   ├── domain/                        # regras de negócio puras
│   │   ├── entities/
│   │   │   ├── asset.py               # 15 tipos de ativos (AssetType enum)
│   │   │   ├── portfolio.py           # portfólio com lógica (retorno, risco, reserva)
│   │   │   ├── alm_entities.py        # entidades ALM: fluxo, portfólio, solvência
│   │   │   └── investor_profile.py    # perfil do investidor
│   │   ├── value_objects/
│   │   │   └── allocation.py          # alocação com IR regressivo e custódia B3
│   │   └── interfaces/                # contratos (repository & service)
│   │
│   ├── application/                   # casos de uso e serviços
│   │   ├── services/
│   │   │   ├── portfolio_builder.py   # motor principal: catálogo + Markowitz + heurística
│   │   │   ├── alm_engine.py          # orquestrador ALM: taxa de equilíbrio, solvência
│   │   │   ├── alm_markowitz.py       # fronteira eficiente RPPS (10 portfólios)
│   │   │   ├── actuarial_flow_parser.py  # parser CadPrev CSV
│   │   │   ├── markowitz_optimizer.py    # otimização mean-variance (max Sharpe)
│   │   │   ├── monte_carlo_engine.py     # simulação estocástica (5k cenários PF / 1k RPPS)
│   │   │   ├── risk_metrics_engine.py    # VaR, Sharpe, Treynor, Drawdown, TE, IR
│   │   │   ├── stress_test_engine.py     # backtest e crises históricas
│   │   │   ├── gap_analysis_engine.py    # gap entre carteira atual e recomendada
│   │   │   ├── quiz_service.py           # suitability quiz (28 perguntas)
│   │   │   └── tax_calculator.py         # IR regressivo + IOF
│   │   └── use_cases/
│   │       ├── generate_portfolio.py
│   │       ├── analyze_portfolio.py
│   │       └── analyze_gap.py
│   │
│   ├── infrastructure/                # implementações técnicas
│   │   ├── database/                  # SQLAlchemy 2.0 + Alembic
│   │   ├── external/
│   │   │   ├── bcb_api.py             # BCB SGS + Focus API (Olinda)
│   │   │   ├── macro_scenario_service.py  # trajetórias Selic/IPCA/CDI
│   │   │   └── market_data_service.py     # retornos históricos por classe
│   │   └── repositories/
│   │
│   ├── alm/
│   │   └── config/                    # configs reais de RPPS (JSON)
│   │       ├── ipsemb_2026.json       # portfólio real IPSEMB (R$188M, abril/2026)
│   │       └── ipsemb_2025_lema.json  # referência LEMA para validação
│   │
│   └── presentation/
│       └── web/
│           ├── routers/web_router.py  # FastAPI routes
│           └── templates/             # Jinja2 + Chart.js
│
├── tests/
│   ├── unit/
│   └── integration/
├── migrations/                        # Alembic
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Stack Tecnológica

| Camada | Tecnologia |
|---|---|
| **Backend** | Python 3.12, FastAPI, Uvicorn |
| **Banco de Dados** | SQLite (dev) / PostgreSQL (prod), SQLAlchemy 2.0 async |
| **Otimização** | NumPy, SciPy (Markowitz, método de Brent) |
| **IA Generativa** | OpenAI GPT-4o-mini (parecer narrativo em PT-BR) |
| **Dados Macroeconômicos** | BCB SGS API, BCB Focus API (Olinda) |
| **Relatórios** | ReportLab, WeasyPrint (PDF) |
| **Frontend** | Jinja2, Chart.js |
| **Pagamentos** | MercadoPago |
| **Infra** | Docker, Render |

---

## Como Executar

### Pré-requisitos

- Docker e Docker Compose instalados
- Chave de API da OpenAI

### Setup

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/proinvestai.git
cd proinvestai

# 2. Configure as variáveis de ambiente
cp .env.example .env
# Edite .env com sua OPENAI_API_KEY e configurações do banco

# 3. Suba o ambiente
docker-compose up --build

# 4. Acesse
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### Executar Testes

```bash
docker-compose exec app pytest tests/ -v
```

### Executar Estudo ALM (RPPS)

```bash
# Com configuração de RPPS existente
python -c "
from app.alm.config import ipsemb_2026
from app.application.services.alm_engine import run_full_alm_study
result = run_full_alm_study('app/alm/config/ipsemb_2026.json')
print(result)
"
```

---

## Módulo ALM — Metodologia

O engine de ALM replica a metodologia utilizada por consultorias especializadas em RPPS:

1. **Parser CadPrev** — lê o CSV de fluxo atuarial (receitas e despesas por ano)
2. **Taxa de Equilíbrio** — encontra a taxa mínima de retorno real que zera o VPL do passivo (método de Brent, tolerância 1e-6)
3. **Fronteira Eficiente** — Markowitz com 10 portfólios, constraints da CMN 5.272/2025 por artigo regulatório e nível de governança (Pro Gestão)
4. **Trava de Iliquidez** — posições de vértice são travadas (flag `is_locked`) e os pesos restantes são otimizados
5. **NTN-B Liability Matching** — casamento de duração entre NTN-Bs e passivo atuarial projetado
6. **Monte Carlo de Solvência** — 1.000 trajetórias de retorno para estimar probabilidade de insolvência
7. **Recomendação** — portfólio de maior Sharpe dentro das restrições regulatórias e da Política de Investimentos

---

## Variáveis de Ambiente

```env
# Banco de dados
DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/proinvestai

# OpenAI
OPENAI_API_KEY=sk-...

# MercadoPago (monetização)
MERCADOPAGO_ACCESS_TOKEN=...

# Segurança
SECRET_KEY=...
```

---

## Roadmap

- [ ] Interface web completa (quiz → portfólio → dashboard)
- [ ] Autenticação e planos de assinatura (Free / Premium / Pro)
- [ ] Geração de PDF do relatório completo
- [ ] API pública para integração com sistemas de RPPS
- [ ] Importação automática de portfólio via CSV/XLSX
- [ ] Recálculo automático com novas projeções do Focus
- [ ] Módulo de empréstimos consignados (Art. 12, CMN 5.272/2025)

---

## Licença

Privado. Desenvolvido por [Cleilton Rodrigues](https://portfoliocleilton.onrender.com/).

Certificações: CEA e CPA-20 (ANBIMA) · Membro de Comitê de Investimentos de RPPS
