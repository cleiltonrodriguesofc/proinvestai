from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from ....infrastructure.external.mercadopago_service import MercadoPagoService

router = APIRouter(prefix="/api/billing", tags=["Billing"])
mp_service = MercadoPagoService()

class SubscriptionRequest(BaseModel):
    email: str
    plan_tier: str # 'premium' or 'pro'

@router.post("/subscribe")
async def subscribe(request: SubscriptionRequest):
    # Map tier to MP Plan ID (in a real app this comes from DB or settings)
    plan_map = {
        "premium": "plan_premium_123",
        "pro": "plan_pro_456"
    }
    
    plan_id = plan_map.get(request.plan_tier.lower())
    if not plan_id:
        raise HTTPException(status_code=400, detail="Plano inválido.")
        
    result = await mp_service.create_subscription(request.email, plan_id)
    return result

@router.post("/webhook")
async def webhook(request: Request):
    """
    Endpoint to receive MercadoPago IPN/Webhooks.
    """
    payload = await request.json()
    # Logic to update user subscription status based on payload
    return {"status": "received"}
