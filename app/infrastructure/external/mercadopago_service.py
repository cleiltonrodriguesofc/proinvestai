import mercadopago
from config import get_settings
import logging

settings = get_settings()
logger = logging.getLogger(__name__)

class MercadoPagoService:
    """
    Service to integrate with MercadoPago API for subscriptions.
    """
    def __init__(self):
        self.access_token = settings.MERCADOPAGO_ACCESS_TOKEN
        if self.access_token:
            self.sdk = mercadopago.SDK(self.access_token)
        else:
            self.sdk = None
            logger.warning("MercadoPago access token not found in settings.")

    async def create_subscription(self, email: str, plan_id: str):
        if not self.sdk:
            return {"status": "error", "message": "Integração de pagamento não configurada."}
            
        # Logic to create subscription based on pre-approval plan
        # This is a mocked implementation
        subscription_data = {
            "preapproval_plan_id": plan_id,
            "payer_email": email,
            "back_url": f"{settings.APP_URL}/dashboard?payment=success",
            "reason": "ProInvestAI Subscription"
        }
        
        try:
            # result = self.sdk.preapproval().create(subscription_data)
            # return result["response"]
            return {"status": "pending", "init_point": "https://www.mercadopago.com.br/mock-checkout"}
        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            return {"status": "error", "message": str(e)}
