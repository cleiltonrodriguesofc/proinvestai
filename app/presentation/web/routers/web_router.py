import json
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path
from ....application.services.quiz_service import QuizService

router = APIRouter()
quiz_service = QuizService()

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
    questions = quiz_service.get_questions()
    # Convert to serializable dict for JSON
    questions_data = []
    for q in questions:
        questions_data.append({
            "id": q.id,
            "text": q.text,
            "section": q.section,
            "options": [{"id": o.id, "text": o.text, "score": o.score} for o in q.options]
        })
        
    return templates.TemplateResponse("quiz.html", {
        "request": request,
        "questions_json": json.dumps(questions_data)
    })
