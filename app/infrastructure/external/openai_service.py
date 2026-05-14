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

    async def explain_gap(self, current_portfolio: dict, ideal_portfolio: dict, profile: InvestorProfile | None = None) -> str:
        """
        Generates a narration explaining the gap between current and ideal allocation.
        """
        if not self.api_key:
            return "Integração com IA não configurada. Configure a API Key para receber insights personalizados."

        # Compute potential gain lost for demonstration
        # In a real app this would come from the gap analysis engine
        current_alloc_str = str({k: v for k, v in current_portfolio.items() if v > 0})
        ideal_alloc_str = str({alloc.asset.name: float(alloc.weight) for alloc in ideal_portfolio.allocations})

        prompt = f"""
        Você é um consultor financeiro profissional nível CEA. 
        Analise a carteira do usuário e explique em português simples (mas profissional) por que a alocação ideal é melhor.
        
        Carteira Atual: {current_alloc_str}
        Carteira Ideal: {ideal_alloc_str}
        Perfil: {profile.risk_profile.value if hasattr(profile, 'risk_profile') and hasattr(profile.risk_profile, 'value') else 'Moderado'}
        
        Siga estas regras:
        1. Fale diretamente com o usuário ("Você", "Sua carteira").
        2. Explique o conceito de risco/retorno de forma educativa.
        3. Seja encorajador mas firme sobre a necessidade de rebalanceamento.
        4. Use no máximo 150 palavras.
        """
        return await self._call_openai(prompt)

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
