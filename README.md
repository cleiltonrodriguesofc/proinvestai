# ProInvestAI

Plataforma de Governança Previdenciária e Investimentos Inteligentes para **RPPS (Regimes Próprios de Previdência Social)**. O ProInvestAI utiliza ciência de dados, modelos quantitativos (Markowitz, ALM) e Inteligência Artificial para monitorar, otimizar e garantir a conformidade (compliance) de carteiras bilionárias de institutos de previdência municipais e estaduais.

## O Que a Plataforma Faz

O ProInvestAI substitui o trabalho braçal e planilhas por uma automação de grau institucional:

1. **Monitoramento de Enquadramento CMN 5.272**: Acompanhamento diário da carteira do RPPS contra as resoluções do Conselho Monetário Nacional (limites por segmento, limites por fundo).
2. **Atualização Diária via CVM**: Sincronização automática das posições do instituto usando os dados públicos e oficiais de cotas diárias da CVM e classificação ANBIMA.
3. **Relatórios Regulatórios Automáticos**: Geração inteligente dos relatórios obrigatórios **DAIR** (Demonstrativo de Aplicações e Investimentos dos Recursos) e **DPIN** (Demonstrativo da Política de Investimentos).
4. **Estudo ALM (Asset Liability Management)**: Projeções estocásticas (Monte Carlo) cruzando o passivo atuarial com o ativo financeiro para prever solvência de longo prazo.
5. **Comitê de Investimentos com IA**: Geração automática de atas, pareceres e análise de risco (VaR, Sharpe) impulsionada por GPT-4 para o Comitê de Investimentos, facilitando as certificações do Pró-Gestão.

## A Solução (Problema x Produto)

| Gestão Tradicional (Planilhas) | Com ProInvestAI |
|---|---|
| Preenchimento manual de DAIR/DPIN | Relatórios gerados automaticamente com 1 clique |
| Risco alto de desenquadramento da CMN | Alertas proativos e monitoramento em tempo real |
| Estudos ALM caros e demorados (Consultorias) | ALM integrado no painel com simulações instantâneas |
| Cotas e rentabilidade calculadas com atraso | Sincronização diária de cotas direto da fonte (CVM) |
| Pareceres do comitê rasos e manuais | IA que redige pareceres técnicos com base matemática |

## Como Executar (Docker)

A aplicação é containerizada e utiliza variáveis de ambiente para segurança. Nenhuma credencial está hardcoded no repositório.

1. Clone o repositório
2. Crie o arquivo `.env` baseado no `.env.example`:
   ```bash
   cp .env.example .env
   ```
   *Preencha o `SECRET_KEY` e as chaves de API (OpenAI).*
3. Execute:
   ```bash
   docker-compose up --build
   ```
4. Acesse: `http://localhost:8000`

## Arquitetura (Clean Architecture)

O projeto segue rigorosamente o padrão **Clean Architecture**, isolando as regras de negócio previdenciário do framework web e banco de dados:

```
app/
├── domain/                    # Entidades puras e regras de negócio
│   ├── entities/
│   │   ├── rpps_entities.py   # RppsInstitute, FundPosition, FundQuote
│   │   ├── portfolio.py       # Portfólio com lógica (retorno, VaR, limites CMN)
│   │   └── alm_entities.py    # Entidades de passivo e teste de solvência
├── application/               # Casos de uso e serviços
│   └── services/
│       ├── cvm_sync_service.py    # Orquestrador de importação da CVM
│       ├── compliance_engine.py   # Validação de regras da CMN 5.272
│       ├── monte_carlo_engine.py  # Simulação estocástica (ALM)
│       └── report_service.py      # Geração de DAIR e Atas
├── infrastructure/            # Implementações técnicas e integrações
│   ├── database/
│   │   ├── models.py          # SQLAlchemy Models (RppsInstitute, etc)
│   │   └── connection.py      # AsyncSession
│   ├── external/
│   │   ├── cvm_api.py         # Consumo dos dados abertos da CVM
│   │   ├── bcb_api.py         # BCB SGS + Focus API
│   │   └── openai_service.py  # GPT-4o para redação de pareceres
│   └── repositories/          # Repositórios de persistência
└── presentation/              # Camada de entrega (FastAPI)
    └── web/
        ├── routers/           # FastAPI routes
        └── templates/         # Jinja2 templates (Dashboards e UI)
```

## Tecnologias

- **Backend**: Python 3.12, FastAPI
- **Database**: PostgreSQL (Prod) / SQLite (Dev) com SQLAlchemy 2.0 (Async)
- **Math/Quant**: NumPy, SciPy (VaR, Markowitz Optimization, Monte Carlo)
- **AI**: OpenAI GPT-4o (Pareceres e Atas)
- **Data Sources**: CVM Dados Abertos (Cotas), ANBIMA (Benchmarks), BCB SGS
- **Frontend**: Jinja2, Vanilla CSS, Chart.js
- **Infraestrutura**: Docker, Uvicorn, Deploy no Render

## Histórico de Versão (Pivot)

O projeto iniciou como uma ferramenta B2C focada no investidor pessoa física (Varejo). Para preservar esse trabalho, o código do varejo foi congelado na tag `v1.0-retail` e na branch `retail/v1`. Atualmente, a branch principal (`main`/`development`) é exclusivamente dedicada ao mercado B2B Institucional (RPPS).

## Licença

Privado. Desenvolvido por Cleilton Rodrigues.
