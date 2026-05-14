from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter()

# Get the path to templates
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@router.get("/")
@router.get("/dashboard")
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user_name": "Investidor",
        "profile_type": "Moderado",
        "total_value": "250.000,00",
        "vol": "8.5"
    })

@router.get("/quiz")
async def quiz(request: Request):
    # This will be implemented in the next step
    return templates.TemplateResponse("dashboard.html", {"request": request, "user_name": "Quiz Em Breve"})
