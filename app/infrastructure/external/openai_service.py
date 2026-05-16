import logging
import openai
from typing import Dict, List
from config import get_settings
from ...domain.interfaces.services import IAIService
from ...domain.entities.portfolio import Portfolio
from ...domain.entities.investor_profile import InvestorProfile

settings = get_settings()
logger = logging.getLogger(__name__)

class AIService(IAIService):
    """
    Service to generate financial insights and narrations using AI.
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        if self.api_key:
            openai.api_key = self.api_key

    async def explain_portfolio(self, portfolio: Portfolio, profile: InvestorProfile) -> str:
        if not self.api_key:
            return "Integração com IA não configurada."
            
        prompt = f"Explique de forma simples uma carteira com retorno esperado de {portfolio.expected_return * 100:.1f}% e volatilidade de {portfolio.volatility * 100:.1f}% para um perfil {profile.risk_profile.value}."
        
        return await self._call_openai(prompt)

    async def explain_committee_review(self, target_weights: dict, risk_metrics, profile_type: str) -> str:
        """
        Generates a professional narration explaining the recommended strategy and risk metrics.
        """
        if not self.api_key:
            return "Integração com IA não configurada. Configure a API Key para receber insights personalizados."

        weights_str = str({k: float(v) for k, v in target_weights.items()})
        
        # Format the risk metrics
        risk_str = (
            f"Rentabilidade 12M: {risk_metrics.return_12m * 100:.2f}% | "
            f"VaR 95%: {risk_metrics.var_12m * 100:.2f}% | "
            f"Sharpe: {risk_metrics.sharpe_12m:.2f} | "
            f"Drawdown Max: {risk_metrics.drawdown_12m * 100:.2f}%"
        )

        prompt = f"""
Você é um Gestor de Portfólio (Portfolio Manager) com certificação CFA/CNPI e experiência em Comitês de Investimento Institucionais.
Sua tarefa é gerar um "Parecer Técnico de Alocação" de alto nível para um cliente com patrimônio relevante.

Perfil do Cliente: {profile_type}
Alocação Recomendada (Estratégia de Fronteira Eficiente): {weights_str}
Métricas de Risco Históricas (Janela 12M): {risk_str}

REGRAS DE ANÁLISE TÉCNICA (Nível Institucional):
1. Justifique a diversificação usando conceitos de Teoria Moderna de Portfólio (MPT): Baixa correlação entre classes de ativos (Equity vs Fixed Income vs International).
2. Explique o porquê da proporção de ativos de risco (Ações/Small Caps) versus ativos de proteção (IMA-B/CDI) com base no Perfil {profile_type}.
3. Comente sobre o Índice de Sharpe ({risk_metrics.sharpe_12m:.2f}) como medida de eficiência na entrega de retorno por unidade de risco assumido.
4. Mencione o VaR ({risk_metrics.var_12m * 100:.2f}%) como o limite de perda esperada para um mês normal (95% de confiança).
5. NUNCA mencione ativos que não estão na lista.
6. Seja conciso, denso tecnicamente e institucional. Use no máximo 150 palavras.
"""
        
        logger.info(f"--- AI PROMPT SENDING ---\n{prompt}\n-------------------------")
        
        response_text = await self._call_openai(prompt)
        
        logger.info(f"--- AI RESPONSE RECEIVED ---\n{response_text}\n----------------------------")
        
        return response_text

    async def explain_stress_test(self, results: dict, profile: InvestorProfile) -> str:
        if not self.api_key:
            return "Integracao com IA nao configurada."

        prompt = f"Explique o resultado de um teste de estresse financeiro onde a carteira do cliente sofreu impacto em cenarios de crise: {results}. Perfil: {profile.risk_profile.value}."
        return await self._call_openai(prompt)

    async def explain_portfolio_recommendation(
        self,
        allocation_summary: list,
        profile_label: str,
        total_value: float,
        net_monthly_income: float,
        gross_annual_return: float,
        net_annual_return: float,
        reserve_months: float,
        risk_category: str,
    ) -> str:
        """generate a plain-language explanation of the recommended portfolio."""
        if not self.api_key:
            return "Integracao com IA nao configurada. Configure a API Key para receber insights personalizados."

        alloc_lines = []
        for a in allocation_summary:
            alloc_lines.append(
                f"- {a['asset_name']}: {a['percentage_display']} ({a['value_display']}) "
                f"| Retorno bruto: {a['gross_return_display']} | Liquido: {a['net_return_display']} "
                f"| {a['tax_label']} | {a['liquidity']} | Risco: {a['risk']}"
            )
        alloc_str = "\n".join(alloc_lines)

        prompt = f"""Voce e um consultor financeiro que explica investimentos para pessoas leigas.
Gere um parecer claro e educativo sobre a carteira recomendada abaixo.

Perfil do investidor: {profile_label}
Patrimonio: R$ {total_value:,.2f}
Renda mensal liquida estimada: R$ {net_monthly_income:,.2f}/mes
Retorno bruto anual: {gross_annual_return:.2%} | Liquido (apos IR): {net_annual_return:.2%}
Reserva de emergencia: {reserve_months:.0f} meses de despesas em ativos liquidos
Risco geral: {risk_category}

Composicao da carteira:
{alloc_str}

INSTRUCOES:
1. Explique em linguagem simples o que cada produto faz e por que foi escolhido.
2. Destaque quais sao isentos de imposto e quais tem FGC.
3. Explique o que significa a reserva de emergencia e por que e importante.
4. Se houver renda variavel, explique o risco de forma honesta.
5. Mencione que o retorno liquido ja desconta IR regressivo e custodia B3.
6. Use no maximo 200 palavras. Seja direto e educativo.
7. NAO use jargao tecnico (nada de "fronteira eficiente", "MPT", "VaR").
8. Responda em portugues do Brasil.
"""
        return await self._call_openai(prompt)

    async def explain_gap_analysis(
        self,
        current_weights: dict,
        ideal_allocations: list,
        annual_gap: float,
        gain_lost: float,
        profile_label: str,
    ) -> str:
        """generate a narration comparing current vs ideal portfolio."""
        if not self.api_key:
            return "Integracao com IA nao configurada."

        current_str = "\n".join(f"- {k}: {v:.0%}" for k, v in current_weights.items())
        ideal_str = "\n".join(
            f"- {a['asset_name']}: {a['percentage_display']}" for a in ideal_allocations
        ) if ideal_allocations else "Dados indisponiveis."

        prompt = f"""Voce e um consultor financeiro educativo.
Compare a carteira atual do investidor com a carteira ideal recomendada.

Perfil: {profile_label}

CARTEIRA ATUAL (o que ele tem hoje):
{current_str}

CARTEIRA IDEAL (o que recomendamos):
{ideal_str}

Diferenca de retorno anual: {annual_gap:.2%}
Custo de oportunidade em 5 anos: R$ {gain_lost:,.2f}

INSTRUCOES:
1. Explique de forma simples o que ele esta perdendo por manter a carteira atual.
2. Destaque os beneficios de diversificar (menor risco, isencao de IR, FGC).
3. NAO critique o investidor — seja construtivo.
4. Use no maximo 150 palavras. Portugues do Brasil.
"""
        return await self._call_openai(prompt)

    async def explain_simulation(
        self,
        profile_label: str,
        initial_amount: float,
        p5: float,
        p50: float,
        p95: float,
        stress_tests: list,
        risk_metrics: dict,
    ) -> str:
        """generate a narration explaining the simulation results."""
        if not self.api_key:
            return "Integracao com IA nao configurada."

        stress_lines = []
        for st in stress_tests:
            stress_lines.append(f"- {st['name']}: impacto de {st['impact']:.2%}")
        stress_str = "\n".join(stress_lines) if stress_lines else "Nenhum dado disponivel."

        prompt = f"""Voce e um consultor financeiro que explica simulacoes para investidores leigos.

Perfil: {profile_label}
Patrimonio investido: R$ {initial_amount:,.2f}

SIMULACAO MONTE CARLO (5.000 cenarios, 5 anos):
- Pior cenario (P5): R$ {p5:,.2f}
- Cenario base (mediana): R$ {p50:,.2f}
- Melhor cenario (P95): R$ {p95:,.2f}

METRICAS DE RISCO:
- Retorno bruto anual: {risk_metrics.get('expected_return', 0):.2%}
- Retorno liquido anual: {risk_metrics.get('net_return', 0):.2%}
- Volatilidade: {risk_metrics.get('volatility', 0):.2%}
- Sharpe Ratio: {risk_metrics.get('sharpe', 0):.2f}
- Drawdown maximo: {risk_metrics.get('max_drawdown', 0):.2%}

STRESS TEST (crises historicas):
{stress_str}

INSTRUCOES:
1. Explique o que significa cada cenario (P5, mediana, P95) em linguagem simples.
2. Interprete o Sharpe Ratio de forma educativa (eficiencia risco-retorno).
3. Comente os resultados dos stress tests — o que aconteceria em crises reais.
4. Seja honesto sobre riscos, mas construtivo.
5. Use no maximo 200 palavras. Portugues do Brasil.
6. NAO use jargao tecnico excessivo.
"""
        return await self._call_openai(prompt)


    async def _call_openai(self, prompt: str) -> str:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self.api_key)
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Você é um consultor financeiro especialista com foco em alocação de ativos e gestão de risco institucional."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating AI narration: {e}")
            return f"Não foi possível gerar a narração agora: {str(e)}"
