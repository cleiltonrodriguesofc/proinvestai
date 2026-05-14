import json
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pathlib import Path
from ....application.services.quiz_service import QuizService
from ....application.services.markowitz_optimizer import MarkowitzOptimizer
from ....application.services.monte_carlo_engine import MonteCarloEngine
from ....application.services.stress_test_engine import StressTestEngine
from ....infrastructure.external.bcb_service import BCBService
from ....application.services.ai_service import AIService
from ....application.services.tax_calculator import TaxCalculator
from ....application.use_cases.analyze_portfolio import AnalyzePortfolioUseCase
from ....domain.entities.portfolio import Portfolio, PortfolioAllocation
from ....domain.entities.asset import Asset, AssetClass
from decimal import Decimal

router = APIRouter()
quiz_service = QuizService()

# Initialize services
bcb_service = BCBService()
tax_calc = TaxCalculator()
ai_service = AIService()
monte_carlo = MonteCarloEngine()
stress_test = StressTestEngine(bcb_service, tax_calc)

# Optimizer would need asset data, we'll use a placeholder for now
optimizer = None 

analyze_use_case = AnalyzePortfolioUseCase(
    optimizer=optimizer,
    monte_carlo=monte_carlo,
    stress_test=stress_test,
    ai_service=ai_service
)

# Get the path to templates
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@router.get("/")
@router.get("/dashboard")
async def dashboard(request: Request):
    # Mock current portfolio for demonstration
    asset1 = Asset(name="Tesouro Selic", asset_class=AssetClass.FIXED_INCOME, subclass="post", benchmark="CDI", spread=Decimal("0.0"), tax_exempt=False, min_investment=Decimal("100"), liquidity_days=1)
    asset2 = Asset(name="Ações", asset_class=AssetClass.EQUITY, subclass="growth", benchmark="IBOV", spread=Decimal("0.0"), tax_exempt=False, min_investment=Decimal("1"), liquidity_days=2)
    
    portfolio = Portfolio(
        allocations=[
            PortfolioAllocation(asset=asset1, weight=Decimal("0.8")),
            PortfolioAllocation(asset=asset2, weight=Decimal("0.2"))
        ],
        expected_return=Decimal("0.11"),
        volatility=Decimal("0.05"),
        sharpe_ratio=Decimal("0.8")
    )
    
    analysis = await analyze_use_case.execute(portfolio, initial_amount=100000.0)
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user_name": "Investidor",
        "profile_type": "Moderado",
        "total_value": "100.000,00",
        "vol": analysis["backtest"].get("volatility", 0) * 100 if "backtest" in analysis else 5.0,
        "analysis": analysis,
        "narration": analysis["narration"]
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
