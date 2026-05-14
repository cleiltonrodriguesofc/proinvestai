import json
from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from ....application.services.quiz_service import QuizService
from ....application.services.markowitz_optimizer import MarkowitzOptimizer
from ....application.services.monte_carlo_engine import MonteCarloEngine
from ....application.services.stress_test_engine import StressTestEngine
from sqlalchemy.ext.asyncio import AsyncSession
from ....infrastructure.external.bcb_service import BCBService
from ....infrastructure.external.openai_service import AIService
from ....application.services.tax_calculator import TaxCalculator
from ....application.use_cases.analyze_portfolio import AnalyzePortfolioUseCase
from ....domain.entities.portfolio import Portfolio, PortfolioAllocation
from ....domain.entities.asset import Asset, AssetClass
from ....domain.entities.user import User as DomainUser
from .auth import get_current_user
from decimal import Decimal

from ....infrastructure.external.market_data_service import MarketDataService
from ....application.services.risk_metrics_engine import RiskMetricsEngine
from ....infrastructure.repositories.profile_repository import SQLAlchemyProfileRepository
from ....infrastructure.database.connection import get_session

router = APIRouter()
quiz_service = QuizService()
market_data = MarketDataService()
risk_engine = RiskMetricsEngine()

# Initialize engines
bcb_service = BCBService()
tax_calc = TaxCalculator()
ai_service = AIService()
monte_carlo = MonteCarloEngine()
stress_test = StressTestEngine(bcb_service, tax_calc)

# Optimizer would need asset data
optimizer = None 

analyze_use_case = AnalyzePortfolioUseCase(
    optimizer=optimizer,
    monte_carlo=monte_carlo,
    stress_test=stress_test,
    ai_service=ai_service
)

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@router.get("/")
async def landing(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})

@router.get("/pricing")
async def pricing(request: Request):
    return templates.TemplateResponse("pricing.html", {"request": request})

@router.get("/dashboard")
async def dashboard(request: Request, user: DomainUser | None = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    if not user:
        return RedirectResponse(url="/login")
        
    # 1. Fetch user profile
    profile_repo = SQLAlchemyProfileRepository(session)
    profile = await profile_repo.get_by_user_id(user.id)
    
    profile_type = profile.risk_profile.value if profile else "moderate"
    initial_amount = float(profile.initial_amount) if profile else 100000.0
    
    # 2. Define Target Portfolio based on Profile (Institutional weights)
    # This maps to the benchmarks we have in MarketDataService
    if profile_type == "conservative":
        weights = {"IRF-M 1": 0.80, "CDI": 0.15, "IMA-B": 0.05}
    elif profile_type == "aggressive":
        weights = {"IBOVESPA": 0.40, "SMLL": 0.10, "IMA-B": 0.30, "CDI": 0.20}
    else: # moderate
        weights = {"CDI": 0.40, "IMA-B": 0.30, "IRF-M": 0.20, "IBOVESPA": 0.10}

    # 3. Fetch Real Historical Data
    benchmarks = list(weights.keys())
    hist_data = market_data.get_all_benchmarks(benchmarks)
    
    # 4. Calculate Institutional Risk Metrics (Comitê Standard)
    risk_report = risk_engine.compute_portfolio(
        asset_returns=hist_data,
        weights=weights,
        benchmark_name="Meta Atuarial"
    )
    
    # 5. Asset mapping for UI
    asset1 = Asset(name="Renda Fixa Pos", asset_class=AssetClass.FIXED_INCOME, subclass="post", benchmark="CDI", spread=Decimal("0.0"), tax_exempt=False, min_investment=Decimal("100"), liquidity_days=1)
    asset2 = Asset(name="Renda Fixa Inflação", asset_class=AssetClass.FIXED_INCOME, subclass="ipca", benchmark="IMA-B", spread=Decimal("0.0"), tax_exempt=False, min_investment=Decimal("100"), liquidity_days=1)
    
    portfolio = Portfolio(
        allocations=[
            PortfolioAllocation(asset=asset1, weight=Decimal(str(weights.get("CDI", 0.5)))),
            PortfolioAllocation(asset=asset2, weight=Decimal(str(weights.get("IMA-B", 0.5))))
        ],
        expected_return=Decimal(str(risk_report.return_12m)),
        volatility=Decimal(str(risk_report.volatility_12m)),
        sharpe_ratio=Decimal(str(risk_report.sharpe_12m))
    )
    
    # 6. Run Simulations (Monte Carlo)
    analysis = await analyze_use_case.execute(portfolio, initial_amount=initial_amount)
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user_name": user.name,
        "profile_type": profile_type.capitalize(),
        "total_value": f"{initial_amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "risk": risk_report,
        "analysis": analysis,
        "weights": weights,
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
