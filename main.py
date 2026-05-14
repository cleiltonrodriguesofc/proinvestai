from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from config import get_settings
import os
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG
)

# Rate Limiter setup
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Static and Templates
# Ensure directories exist before mounting
os.makedirs("app/presentation/web/static", exist_ok=True)
os.makedirs("app/presentation/web/templates", exist_ok=True)

app.mount("/static", StaticFiles(directory="app/presentation/web/static"), name="static")
templates = Jinja2Templates(directory="app/presentation/web/templates")

from app.presentation.web.routers.web_router import router as web_router
from app.presentation.api.routers.quiz_router import router as quiz_api_router
from app.presentation.web.routers.auth import router as auth_router
from app.presentation.api.routers.billing_router import router as billing_router

app.include_router(web_router)
app.include_router(quiz_api_router)
app.include_router(auth_router)
app.include_router(billing_router)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "app": settings.APP_NAME}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
