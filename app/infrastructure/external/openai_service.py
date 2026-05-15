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
Você é um analista quantitativo sênior (Nível CFA/CEA) do "Comitê Digital" da ProInvestAI.
Sua tarefa é gerar um "Parecer Técnico" curto e institucional sobre a alocação recomendada abaixo para um cliente.

Perfil do Cliente: {profile_type}
Alocação Recomendada: {weights_str}
Métricas de Risco Esperadas da Carteira (Backtest 12M): {risk_str}

REGRAS RÍGIDAS (Siga ou será penalizado):
1. NUNCA mencione ativos ou classes que não estão na "Alocação Recomendada" acima.
2. NUNCA diga que o cliente tem a carteira X (ele ainda não tem). Diga que a ESTRATÉGIA RECOMENDADA foca em Y.
3. Use um tom estritamente profissional, institucional e conciso (máximo de 120 palavras).
4. Explique brevemente por que essa alocação faz sentido para o perfil dele e destaque a segurança (VaR/Drawdown) ou o prêmio de risco (Sharpe).
5. Fale diretamente com o cliente ("Seu comitê digital recomenda...", "Para o seu perfil...").
"""
        
        logger.info(f"--- AI PROMPT SENDING ---\n{prompt}\n-------------------------")
        
        response_text = await self._call_openai(prompt)
        
        logger.info(f"--- AI RESPONSE RECEIVED ---\n{response_text}\n----------------------------")
        
        return response_text

    async def explain_stress_test(self, results: dict, profile: InvestorProfile) -> str:
        if not self.api_key:
            return "Integração com IA não configurada."
            
        prompt = f"Explique o resultado de um teste de estresse financeiro onde a carteira do cliente sofreu impacto em cenários de crise: {results}. Perfil: {profile.risk_profile.value}."
        return await self._call_openai(prompt)

    async def _call_openai(self, prompt: str) -> str:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self.api_key)
            
            response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Você é um consultor financeiro especialista."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating AI narration: {e}")
            return f"Não foi possível gerar a narração agora: {str(e)}"
