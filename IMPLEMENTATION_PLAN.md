# ProInvestAI — Plano de Implementação

## Visão

Plataforma web que ajuda investidores brasileiros a montarem carteiras profissionais baseadas no seu perfil, usando otimização matemática (Markowitz) e IA para explicar tudo em português simples.

---

## FASE 0 — Fundação (Dia 1)

### Task 0.1: Inicializar repositório
- Criar repo `proinvestai` no GitHub (privado)
- Inicializar com `git init`, criar branch `main` e `development`
- Criar `.gitignore` para Python, Node, Docker, `.env`
- Criar `README.md` com descrição do projeto
- Criar `.env.example` com variáveis necessárias

### Task 0.2: Estrutura Clean Architecture
Criar a seguinte estrutura de diretórios:
```
proinvestai/
├── app/
│   ├── domain/           # entities, value objects, interfaces
│   │   ├── entities/
│   │   ├── value_objects/
│   │   └── interfaces/   # repository & service contracts
│   ├── application/      # use cases, services
│   │   ├── use_cases/
│   │   └── services/
│   ├── infrastructure/   # db, external apis, implementations
│   │   ├── database/
│   │   ├── external/     # bcb, brapi, openai
│   │   └── repositories/
│   └── presentation/     # web routes, templates, static
│       ├── web/
│       │   ├── routers/
│       │   ├── templates/
│       │   └── static/
│       └── api/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── migrations/           # alembic
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── alembic.ini
├── main.py               # entrypoint
└── config.py             # settings
```

### Task 0.3: Docker setup
- `Dockerfile` multi-stage (builder + runtime)
- `docker-compose.yml` com app + postgres
- `.env.example` com todas as variáveis
- Container roda como non-root user
- `.dockerignore` para excluir venv, __pycache__, .git

### Task 0.4: Dependências base
`requirements.txt`:
```
fastapi==0.115.0
uvicorn[standard]==0.30.0
sqlalchemy[asyncio]==2.0.35
alembic==1.13.0
asyncpg==0.29.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
jinja2==3.1.4
python-multipart==0.0.9
httpx==0.27.0
pydantic==2.9.0
pydantic-settings==2.5.0
```

### Task 0.5: Config e entrypoint
- `config.py`: class `Settings` usando pydantic-settings, carrega `.env`
- `main.py`: cria FastAPI app, monta routers, templates, static files
- Health check endpoint: `GET /health`

---

## FASE 1 — Domain Layer (Dia 2)

### Task 1.1: Entity — InvestorProfile
Arquivo: `app/domain/entities/investor_profile.py`
```python
class RiskProfile(str, Enum):
    ULTRACONSERVATIVE = "ultraconservative"
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    ULTRA_AGGRESSIVE = "ultra_aggressive"

@dataclass
class InvestorProfile:
    risk_profile: RiskProfile
    investment_horizon_months: int     # 12, 36, 60, 120, 240
    monthly_income: Decimal            # renda mensal
    initial_amount: Decimal            # quanto vai investir
    monthly_contribution: Decimal      # aporte mensal
    has_emergency_reserve: bool
    investment_goal: str               # "aposentadoria", "casa", "viagem"
    score: int                         # 0-100 do quiz
```

### Task 1.2: Entity — Asset
Arquivo: `app/domain/entities/asset.py`
```python
@dataclass
class Asset:
    name: str                  # "tesouro selic 2029"
    asset_class: AssetClass    # enum: FIXED_INCOME, EQUITY, REAL_ESTATE
    subclass: str              # "tesouro_selic", "cdb_cdi", "lci", "etf"
    benchmark: str             # "selic", "cdi", "ipca", "ibovespa"
    spread: Decimal            # spread sobre benchmark (ex: 1.0 = 100% CDI)
    tax_exempt: bool           # lci/lca = true
    min_investment: Decimal
    liquidity_days: int        # d+0, d+1, d+30
    historical_returns: list   # series de retornos mensais
```

### Task 1.3: Entity — Portfolio
Arquivo: `app/domain/entities/portfolio.py`
```python
@dataclass
class PortfolioAllocation:
    asset: Asset
    weight: Decimal            # 0.0 a 1.0

@dataclass
class Portfolio:
    allocations: list[PortfolioAllocation]
    expected_return: Decimal
    volatility: Decimal
    sharpe_ratio: Decimal
    max_drawdown: Decimal
```

### Task 1.4: Entity — User
Arquivo: `app/domain/entities/user.py`
```python
@dataclass
class User:
    id: UUID
    email: str
    name: str
    hashed_password: str
    phone: str | None
    plan: SubscriptionPlan     # FREE, PREMIUM, PRO
    created_at: datetime
```

### Task 1.5: Entity — UserAsset (tracker)
Arquivo: `app/domain/entities/user_asset.py`
```python
@dataclass
class UserAsset:
    id: UUID
    user_id: UUID
    asset_name: str
    asset_class: AssetClass
    ticker: str | None
    quantity: Decimal
    average_price: Decimal
    purchase_date: date
    current_value: Decimal | None
```

### Task 1.6: Interfaces (contracts)
Arquivo: `app/domain/interfaces/repositories.py`
- `IUserRepository`: create, get_by_email, get_by_id, update
- `IUserAssetRepository`: create, list_by_user, update, delete
- `IProfileRepository`: save_profile, get_by_user

Arquivo: `app/domain/interfaces/services.py`
- `IMarketDataService`: get_selic, get_cdi, get_ipca, get_historical
- `IOptimizerService`: optimize(profile, assets) -> Portfolio
- `IAIService`: explain_portfolio(portfolio, profile) -> str

---

## FASE 2 — Infrastructure Layer (Dia 3-4)

### Task 2.1: Database models (SQLAlchemy)
Arquivo: `app/infrastructure/database/models.py`
- UserModel: id, email, name, hashed_password, phone, plan, created_at
- InvestorProfileModel: id, user_id, risk_profile, horizon, income, amount, contribution, has_reserve, goal, score, created_at
- UserAssetModel: id, user_id, asset_name, asset_class, ticker, quantity, avg_price, purchase_date, current_value, updated_at
- SimulationModel: id, user_id, profile_id, result_json, created_at

### Task 2.2: Database connection
Arquivo: `app/infrastructure/database/connection.py`
- async engine com asyncpg
- async session factory
- get_session dependency

### Task 2.3: Alembic setup
- `alembic init migrations`
- configurar `env.py` para usar async
- criar migration inicial com todas as tabelas

### Task 2.4: Repository implementations
Arquivo: `app/infrastructure/repositories/user_repository.py`
Arquivo: `app/infrastructure/repositories/user_asset_repository.py`
Arquivo: `app/infrastructure/repositories/profile_repository.py`
- implementar todos os métodos definidos nas interfaces

### Task 2.5: BCB Market Data Service
Arquivo: `app/infrastructure/external/bcb_service.py`
- COPIAR de: `INVESTIMENTO ANA/infrastructure/market_data/bcb_historical.py`
- ADAPTAR: extrair Selic, CDI, IPCA séries do SGS
- ADICIONAR: cache em memória (TTL 24h) para não bater na API a cada request
- Endpoint SGS: `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{serie}/dados`
- Series: Selic (432), CDI (12), IPCA (433)

### Task 2.6: BCB Focus Service
Arquivo: `app/infrastructure/external/bcb_focus_service.py`
- COPIAR de: `INVESTIMENTO ANA/infrastructure/market_data/macro_scenario.py`
- Buscar projeções Focus (Selic terminal, IPCA projetado)
- Cache 24h

### Task 2.7: OpenAI Service
Arquivo: `app/infrastructure/external/openai_service.py`
- COPIAR base de: `whatsapp_sales_agent/core/infrastructure/services/openai_service.py`
- Método: `explain_portfolio(portfolio, profile) -> str`
- Prompt template: recebe dados do portfólio + perfil, gera explicação em PT-BR
- Model: gpt-4o-mini (custo ~$0.0015/request)
- Timeout: 30s, retry: 2x

---

## FASE 3 — Application Layer (Dia 5-6)

### Task 3.1: Suitability Quiz Engine (Assessoria Digital CEA)
Arquivo: `app/application/services/suitability_engine.py`

Baseado no guia real de assessoria profissional. 7 seções, 28 perguntas.
O quiz é apresentado como wizard (uma seção por tela) para não assustar o usuário.
Algumas perguntas são de múltipla escolha (pontuadas) e outras são campos abertos (usadas pela IA para personalizar a análise, mas não pontuadas).

**Seção 1 — Informações Gerais (dados do perfil)**
```
Q1: qual a sua principal fonte de renda?
    → campo texto (dado para IA, não pontuado)

Q2: possui outras fontes de renda?
    a) não (0pts)  b) sim, renda extra informal (2pts)
    c) sim, aluguéis ou dividendos (4pts)  d) sim, negócio próprio (4pts)

Q3: qual sua renda mensal aproximada?
    a) até R$3.000 (2pts)  b) R$3.000-7.000 (4pts)
    c) R$7.000-15.000 (6pts)  d) acima de R$15.000 (8pts)

Q4: qual sua despesa mensal aproximada?
    → campo numérico (usado para calcular capacidade de aporte)

Q5: possui dependentes?
    a) não (0pts)  b) 1-2 (0pts)  c) 3 ou mais (0pts)
    → não pontua, mas influencia recomendação de reserva
```

**Seção 2 — Diagnóstico Financeiro**
```
Q6: valor disponível para investir agora?
    a) até R$5.000 (2pts)  b) R$5.000-20.000 (4pts)
    c) R$20.000-100.000 (6pts)  d) acima de R$100.000 (8pts)

Q7: possui reserva de emergência (6 meses de gastos)?
    a) não tenho (0pts)  b) tenho parcial (3pts)  c) sim, completa (5pts)

Q8: possui imóveis?
    a) não (0pts)  b) sim, onde moro (1pt)  c) sim, incluindo imóveis de renda (3pts)

Q9: possui financiamentos, empréstimos ou dívidas?
    a) sim, em atraso (-5pts)  b) sim, em dia (0pts)  c) não (3pts)

Q10: quanto sobra mensalmente para investir?
    → campo numérico (usado para calcular aporte mensal sugerido)
```

**Seção 3 — Objetivos Financeiros**
```
Q11: qual o principal objetivo dos seus investimentos?
    a) criar reserva de emergência (2pts)
    b) gerar renda mensal (4pts)
    c) aposentadoria (6pts)
    d) crescimento patrimonial (8pts)
    e) comprar bem específico (casa, carro) (4pts)

Q12: possui metas de curto prazo (até 1 ano)?
    → campo texto (usado pela IA para sugerir liquidez)

Q13: possui metas de médio prazo (1-5 anos)?
    → campo texto (usado pela IA)

Q14: possui metas de longo prazo (5+ anos)?
    → campo texto (usado pela IA)
```

**Seção 4 — Perfil de Risco (seção mais importante para scoring)**
```
Q15: prefere segurança ou maior rentabilidade?
    a) segurança total (2pts)  b) mais segurança que rentabilidade (4pts)
    c) equilíbrio (6pts)  d) mais rentabilidade que segurança (8pts)
    e) máxima rentabilidade (10pts)

Q16: aceita oscilações nos investimentos?
    a) não aceito nenhuma oscilação (2pts)
    b) aceito oscilações de até 5% (4pts)
    c) aceito oscilações de até 15% (6pts)
    d) aceito oscilações maiores se o retorno compensar (10pts)

Q17: como reagiria diante de perdas temporárias de 10%?
    a) venderia tudo imediatamente (2pts)
    b) venderia parte para reduzir risco (4pts)
    c) manteria e esperaria recuperar (6pts)
    d) compraria mais aproveitando o preço baixo (10pts)

Q18: já investiu em renda variável (ações, FIIs, ETFs)?
    a) nunca (2pts)  b) sim, mas tive experiência ruim (3pts)
    c) sim, pouco (5pts)  d) sim, regularmente (8pts)

Q19: qual nível de risco considera confortável?
    a) zero risco (2pts)  b) risco muito baixo (4pts)
    c) risco moderado (6pts)  d) risco alto (8pts)
```

**Seção 5 — Liquidez e Disponibilidade**
```
Q20: pode deixar o dinheiro investido por quanto tempo?
    a) preciso de liquidez diária (2pts)  b) até 1 ano (4pts)
    c) 1-5 anos (6pts)  d) 5-10 anos (8pts)
    e) mais de 10 anos (10pts)

Q21: existe possibilidade de precisar do valor rapidamente?
    a) sim, alta probabilidade (2pts)  b) talvez (4pts)
    c) improvável (6pts)  d) não, tenho reserva separada (8pts)

Q22: quanto precisa manter disponível (liquidez diária)?
    → campo numérico (usado para reservar parte em Selic/CDB liquidez)
```

**Seção 6 — Conhecimento Financeiro**
```
Q23: conhece renda fixa (CDB, LCI, Tesouro)?
    a) não conheço (2pts)  b) já ouvi falar (3pts)
    c) conheço e já investi (5pts)

Q24: conhece fundos imobiliários (FIIs)?
    a) não conheço (2pts)  b) já ouvi falar (3pts)
    c) conheço e já investi (5pts)

Q25: tem interesse em aprender mais sobre investimentos?
    a) prefiro algo simples e automático (2pts)
    b) quero entender o básico (4pts)
    c) quero aprender e acompanhar (6pts)
```

**Seção 7 — Expectativas**
```
Q26: qual rendimento mensal/anual considera satisfatório?
    → campo texto (usado pela IA para calibrar expectativas)

Q27: o que espera dos seus investimentos?
    a) não perder para inflação (2pts)
    b) render mais que poupança (4pts)
    c) render acima do CDI (6pts)
    d) máximo retorno possível (8pts)

Q28: como define sua relação com dinheiro?
    → campo texto (usado pela IA para tom da explicação)
```

**Scoring (perguntas pontuadas: Q2,Q3,Q6,Q7,Q8,Q9,Q11,Q15,Q16,Q17,Q18,Q19,Q20,Q21,Q23,Q24,Q25,Q27)**
Score total (0-120) → classificação:
- 0-30: ultraconservador
- 31-50: conservador
- 51-70: moderado
- 71-90: arrojado
- 91-120: agressivo

**Campos de texto (Q1,Q4,Q5,Q10,Q12,Q13,Q14,Q22,Q26,Q28)**
Não pontuam, mas são enviados para a IA gerar uma explicação personalizada.
Exemplo: se Q28 = "tenho medo de perder dinheiro", a IA usa tom mais educativo e tranquilizador.

> [!IMPORTANT]
> Diferencial competitivo: nenhum simulador online faz perguntas desse nível.
> Isso é literalmente uma assessoria CEA digital. O usuário sente que
> está sendo atendido por um profissional, não preenchendo um formulário.

### Task 3.2: Markowitz Optimizer
Arquivo: `app/application/services/markowitz_optimizer.py`
- COPIAR de: `INVESTIMENTO ANA/application/scenario_builder.py`
- Input: InvestorProfile + lista de Assets com histórico
- Output: Portfolio com pesos otimizados
- Lógica: minimizar variância sujeito a retorno-alvo OU maximizar Sharpe
- Usar scipy.optimize.minimize com constraints
- Ajustar pesos conforme perfil (ultraconservador = max 0% RV, agressivo = até 30% RV)

### Task 3.3: Backtest Engine
Arquivo: `app/application/services/backtest_engine.py`
- COPIAR de: `INVESTIMENTO ANA/application/stochastic_engine.py`
- Input: Portfolio + período histórico
- Output: série de retornos, drawdown, retorno acumulado, volatilidade realizada
- Usar dados BCB reais (2015-2026)

### Task 3.4: Stress Test Engine
Arquivo: `app/application/services/stress_test_engine.py`
- COPIAR de: `INVESTIMENTO ANA/domain/entities/stress_test.py`
- Cenários: Joesley Day (mai/2017), COVID (mar/2020), Alta Selic 2022, Circuit Breaker 2008
- Para cada cenário: calcular impacto no portfolio

### Task 3.5: Monte Carlo Engine
Arquivo: `app/application/services/monte_carlo_engine.py`
- COPIAR de: `INVESTIMENTO ANA/application/monte_carlo_engine.py`
- 5.000 simulações bootstrap
- Output: percentis (5, 25, 50, 75, 95), probabilidade de atingir meta

### Task 3.6: Gap Analysis Engine
Arquivo: `app/application/services/gap_analysis_engine.py`
- Input: user_assets (carteira real) + optimized_portfolio (carteira ideal)
- Output: diferenças por classe, diferença em R$, diferença em retorno esperado
- Gerar texto: "você está perdendo ~R$X/ano por ter Y% em poupança"

### Task 3.7: Use Cases
Arquivo: `app/application/use_cases/submit_quiz.py`
- Receber respostas → calcular score → classificar perfil → salvar

Arquivo: `app/application/use_cases/generate_portfolio.py`
- Receber perfil → buscar dados BCB → rodar Markowitz → gerar portfolio → IA explicar

Arquivo: `app/application/use_cases/run_backtest.py`
- Receber portfolio → buscar histórico → calcular backtest → retornar métricas

Arquivo: `app/application/use_cases/track_asset.py`
- CRUD de ativos do usuário

Arquivo: `app/application/use_cases/analyze_gap.py`
- Comparar carteira real vs ideal

---

## FASE 4 — Presentation Layer (Dia 7-10)

### Task 4.1: Auth routes
Arquivo: `app/presentation/web/routers/auth.py`
- POST /register: email, senha, nome → criar user → redirect login
- POST /login: email, senha → gerar JWT → set cookie → redirect dashboard
- GET /logout: limpar cookie → redirect home
- COPIAR lógica de: `whatsapp_sales_agent/core/presentation/web/routers/auth.py`

### Task 4.2: Landing page
Arquivo: `app/presentation/web/templates/landing.html`
- Hero: "Monte sua carteira profissional em 5 minutos — grátis"
- Badges: "Desenvolvido por Gestor CEA" + "IA + Dados BCB ao vivo"
- CTA: "Começar Quiz Gratuito"
- Sections: Como funciona (3 passos), Features, Preços, FAQ
- Footer: Disclaimer CVM, contato, redes sociais
- Design: dark mode, glassmorphism, gradients, Google Fonts (Inter)

### Task 4.3: Quiz page
Arquivo: `app/presentation/web/templates/quiz.html`
- 10 perguntas, uma por vez (step wizard com JS)
- Barra de progresso animada
- Botões de resposta com hover effects
- Ao final: "Calculando seu perfil..." (animação de loading)
- Redirect para resultado

### Task 4.4: Resultado do quiz (FREE)
Arquivo: `app/presentation/web/templates/quiz_result.html`
- Badge do perfil (cor + ícone)
- Gráfico pizza com alocação ideal (Chart.js)
- Retorno esperado básico (sem detalhamento)
- CTA: "Ver análise completa" → cadastro
- CTA: "Compartilhar meu perfil" → share card (viral)

### Task 4.5: Dashboard (PREMIUM)
Arquivo: `app/presentation/web/templates/dashboard.html`
- Patrimônio total (card com animação)
- Rentabilidade acumulada (line chart - Chart.js)
- Divisão por classe (doughnut chart)
- Lista de ativos com preço médio e valor atual
- Botão: "+ Adicionar Ativo"

### Task 4.6: Simulação completa (PREMIUM)
Arquivo: `app/presentation/web/templates/simulation.html`
- Portfolio otimizado (Markowitz) com pesos detalhados
- Backtest chart (2015-2026) vs CDI vs Ibovespa vs Poupança
- Métricas: Sharpe, Vol, Max Drawdown, Retorno Anualizado
- IA Narradora: bloco de texto gerado pelo GPT explicando tudo
- Stress test cards (COVID, Joesley, etc.)
- Monte Carlo: fan chart com IC 95%
- Botão: "Baixar PDF"

### Task 4.7: Gap Analysis (PREMIUM)
Arquivo: `app/presentation/web/templates/gap_analysis.html`
- Side-by-side: carteira real vs carteira ideal
- Diferença em R$/ano
- IA explicando o gap
- CTA: "Falar com Assessor CEA" → WhatsApp ou Calendly

### Task 4.8: Pricing page
Arquivo: `app/presentation/web/templates/pricing.html`
- 3 cards: Free, Premium (R$9,90), Pro (R$29,90)
- Feature comparison table
- CTA: "Começar Grátis" / "Assinar Premium"
- Integração MercadoPago

### Task 4.9: Static files e CSS
Arquivo: `app/presentation/web/static/css/main.css`
- Design system: variáveis CSS, dark mode, tipografia Inter
- Componentes: cards, buttons, forms, charts, badges, modals
- Animações: fade-in, slide-up, pulse, skeleton loading
- Responsivo: mobile-first

Arquivo: `app/presentation/web/static/js/main.js`
- Quiz wizard (step control)
- Chart.js initialization
- HTMX interactions
- Share functionality

---

## FASE 5 — Billing & Polish (Dia 11-12)

### Task 5.1: MercadoPago integration
- COPIAR de: `whatsapp_sales_agent/core/infrastructure/services/mercadopago_service.py`
- Criar subscription plans: Premium e Pro
- Webhook para confirmação de pagamento
- Middleware para verificar plano ativo

### Task 5.2: PDF Report generator
- Usar WeasyPrint ou ReportLab
- Template HTML → PDF com logo, gráficos (base64), texto IA
- Download endpoint: GET /report/download

### Task 5.3: Rate limiting & security
- COPIAR de: whatsapp_sales_agent (rate limiting, CORS, CSP, HSTS)
- Limitar quiz: 5/hora por IP
- Limitar simulações: 10/dia para free, ilimitado para premium

---

## FASE 6 — Testes & Deploy (Dia 13-14)

### Task 6.1: Unit tests
- test_suitability_engine.py: testar scoring e classificação
- test_markowitz_optimizer.py: testar otimização com dados mock
- test_backtest_engine.py: testar cálculos de retorno
- test_gap_analysis.py: testar comparação real vs ideal

### Task 6.2: Integration tests
- test_bcb_service.py: testar conexão BCB real
- test_auth_flow.py: register → login → access dashboard
- test_quiz_flow.py: submeter quiz → ver resultado

### Task 6.3: Deploy
- `render.yaml` com web service + postgres
- Variáveis de ambiente no Render
- DNS: apontar proinvestai.com.br → Render
- SSL automático via Render

---

## Ordem de Execução (para a IA executar)

```
FASE 0 → FASE 1 → FASE 2 → FASE 3 → FASE 4 → FASE 5 → FASE 6
```

Cada fase depende da anterior. Não pular fases.
Cada task dentro de uma fase pode ser executada em sequência.
Commitar ao final de cada FASE completa.
Branch: `feature/fase-X` → PR para `development`.
