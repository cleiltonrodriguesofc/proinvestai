# ProInvestAI

Plataforma de investimentos inteligente que utiliza o modelo de Markowitz e IA para ajudar investidores brasileiros a montarem carteiras profissionais com **produtos reais investíveis** (Tesouro Direto, CDB, LCI/LCA, FIIs, ETFs, etc.).

## O Que a Plataforma Faz

1. **Análise de Perfil (Suitability)**: Quiz de 28 perguntas que classifica o investidor (Conservador, Moderado, Arrojado).
2. **Montagem de Carteira Real**: Otimização Markowitz com 15 produtos reais do mercado brasileiro, constraints por perfil (reserva de emergência, limite de renda variável, diversificação).
3. **Projeções Forward**: Projeção ano-a-ano usando dados do BCB Focus (Selic/IPCA), com IR regressivo e custódia B3.
4. **Simulação Monte Carlo**: 5.000 cenários estocásticos para projetar patrimônio futuro.
5. **Gap Analysis**: Comparação entre carteira atual e recomendada.
6. **Parecer com IA**: Narração personalizada via GPT-4o sobre a composição e riscos.

## Motor de Carteira

O motor constrói carteiras com **produtos reais**:

| Produto | Retorno | Imposto | Liquidez | Proteção |
|---|---|---|---|---|
| Tesouro Selic 2031 | Selic + 0,08% | IR Regressivo | D+1 | Governo Federal |
| CDB Liquidez Diária | 100% CDI | IR Regressivo | D+0 | FGC R$250k |
| LCI/LCA 93% CDI | 93% CDI | **Isento** | D+90 | FGC R$250k |
| Tesouro IPCA+ 2032 | IPCA + 7,61% | IR Regressivo | D+1 | Governo Federal |
| IPCA+ Juros Semestrais 2037 | IPCA + 7,38% | IR Regressivo | D+1 (cupons jan/jul) | Governo Federal |
| Debênture Incentivada | IPCA + 7,0% | **Isento** | D+30 | Risco de crédito |
| FII (IFIX) | IPCA + 5,5% | **Isento** (dividendos) | D+3 | Mercado |
| ETF Ibovespa (BOVA11) | IPCA + 8,5% | IR 15% | D+3 | Mercado |
| ETF S&P 500 (IVVB11) | ~10% USD | IR 15% | D+3 | Mercado |
| Mais 6 produtos... | | | | |

### Constraints por Perfil

| Perfil | Max Renda Variável | Reserva Emergência | Min Líquido |
|---|---|---|---|
| Conservador | 5% | 12 meses | 35% |
| Moderado | 20% | 6 meses | 20% |
| Arrojado | 40% | 3 meses | 10% |

## Como Executar (Docker)

1. Clone o repositório
2. Crie o arquivo `.env` baseado no `.env.example`
3. Execute:
   ```bash
   docker-compose up --build
   ```
4. Acesse: `http://localhost:8000`

## Arquitetura

O projeto segue **Clean Architecture**:

```
app/
├── domain/                    # entidades e regras de negócio
│   ├── entities/
│   │   ├── asset.py           # 15 tipos de ativos (AssetType enum)
│   │   ├── portfolio.py       # portfólio com lógica (retorno, risco, reserva)
│   │   └── investor_profile.py
│   └── value_objects/
│       └── allocation.py      # alocação com IR regressivo e custódia B3
├── application/               # casos de uso e serviços
│   └── services/
│       ├── portfolio_builder.py   # motor principal (Markowitz + catálogo real)
│       ├── markowitz_optimizer.py # otimização mean-variance
│       ├── monte_carlo_engine.py  # simulação estocástica
│       ├── risk_metrics_engine.py # VaR, Sharpe, Drawdown
│       └── quiz_service.py        # suitability quiz (28 perguntas)
├── infrastructure/            # implementações técnicas
│   └── external/
│       ├── bcb_api.py             # BCB SGS + Focus API
│       ├── macro_scenario_service.py # cenário macro (Selic/IPCA/CDI)
│       └── market_data_service.py    # dados históricos
└── presentation/              # camada de entrega
    └── web/
        ├── routers/web_router.py  # FastAPI routes
        └── templates/             # Jinja2 templates
```

## Tecnologias

- **Backend**: Python 3.12, FastAPI
- **Database**: SQLite (dev) / PostgreSQL (prod), SQLAlchemy 2.0
- **Math**: NumPy, SciPy (Markowitz Optimization)
- **AI**: OpenAI GPT-4o-mini
- **Data**: BCB SGS API, BCB Focus API (Olinda)
- **Frontend**: Jinja2, Chart.js
- **Infra**: Docker, Render

## Licença

Privado. Desenvolvido por Cleilton Rodrigues.
