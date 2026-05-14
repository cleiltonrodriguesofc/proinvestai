# ProInvestAI

Plataforma de investimentos inteligente que utiliza o modelo de Markowitz e IA para ajudar investidores brasileiros a montarem carteiras profissionais.

## 🚀 Como Executar (Docker)

1. Clone o repositório
2. Crie o arquivo `.env` baseado no `.env.example`
3. Execute o comando:
   ```bash
   docker-compose up --build
   ```
4. Acesse: `http://localhost:8000`

## 🏗️ Arquitetura

O projeto segue os princípios da **Clean Architecture**:

- `app/domain`: Entidades de negócio e interfaces (contracts).
- `app/application`: Casos de uso e serviços de orquestração.
- `app/infrastructure`: Implementações técnicas (DB, APIs externas).
- `app/presentation`: Camada de entrega (FastAPI, Jinja2).

## 🛠️ Tecnologias

- **Backend**: Python 3.11, FastAPI
- **Database**: PostgreSQL, SQLAlchemy 2.0
- **Math**: Scipy (Markowitz Optimization), Pandas
- **AI**: OpenAI GPT-4o-mini
- **Frontend**: Jinja2, HTMX, Chart.js
- **Infra**: Docker, Render

## 📜 Licença

Privado. Desenvolvido por Cleilton Rodrigues.
