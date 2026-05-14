import logging
import openai
from typing import Dict, List
from config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

class AIService:
    """
    Service to generate financial insights and narrations using AI.
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        if self.api_key:
            openai.api_key = self.api_key

    async def generate_gap_analysis_narration(
        self, 
        current_allocation: Dict[str, float], 
        ideal_allocation: Dict[str, float],
        potential_gain_lost: float
    ) -> str:
        """
        Generates a narration explaining the gap between current and ideal allocation.
        """
        if not self.api_key:
            return "Integração com IA não configurada. Configure a API Key para receber insights personalizados."

        prompt = f"""
        Você é um consultor financeiro profissional nível CEA. 
        Analise a carteira do usuário e explique em português simples (mas profissional) por que a alocação ideal é melhor.
        
        Carteira Atual: {current_allocation}
        Carteira Ideal: {ideal_allocation}
        Estimativa de ganho perdido por ano: R$ {potential_gain_lost:.2f}
        
        Siga estas regras:
        1. Fale diretamente com o usuário ("Você", "Sua carteira").
        2. Destaque o valor em R$ perdido (custo de oportunidade).
        3. Explique o conceito de risco/retorno de forma educativa.
        4. Seja encorajador mas firme sobre a necessidade de rebalanceamento.
        5. Use no máximo 150 palavras.
        """

        try:
            # Using openai v1.x client style if updated, or legacy
            # Assuming newest openai package is installed as per requirements
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
