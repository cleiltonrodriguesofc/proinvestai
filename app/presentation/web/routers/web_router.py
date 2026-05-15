import json
import logging
import numpy as np
from decimal import Decimal
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from ....application.services.quiz_service import QuizService
from ....application.services.markowitz_optimizer import MarkowitzOptimizer
from ....application.services.monte_carlo_engine import MonteCarloEngine
from ....application.services.stress_test_engine import StressTestEngine
from ....application.services.tax_calculator import TaxCalculator
from ....application.services.risk_metrics_engine import RiskMetricsEngine
from ....application.use_cases.analyze_portfolio import AnalyzePortfolioUseCase
from ....domain.entities.portfolio import Portfolio, PortfolioAllocation
from ....domain.entities.asset import Asset, AssetClass
from ....domain.entities.user import User as DomainUser
from ....infrastructure.external.bcb_service import BCBService
from ....infrastructure.external.openai_service import AIService
from ....infrastructure.external.market_data_service import MarketDataService
from ....infrastructure.external.macro_scenario_service import MacroScenarioService
from ....infrastructure.repositories.profile_repository import SQLAlchemyProfileRepository
from ....infrastructure.database.connection import get_session
from ....infrastructure.database.models import InvestorProfile as ProfileModel
from .auth import get_current_user

logger = logging.getLogger(__name__)

# ── shared constants ──

PROFILE_LABELS = {
    "conservative": "Conservador",
    "moderate": "Moderado",
    "aggressive": "Arrojado",
    "ultraconservative": "Ultraconservador",
    "ultra_aggressive": "Ultra Arrojado",
}

# ── service singletons ──

router = APIRouter()
quiz_service = QuizService()
market_data = MarketDataService()
risk_engine = RiskMetricsEngine()
bcb_service = BCBService()
tax_calc = TaxCalculator()
ai_service = AIService()
monte_carlo = MonteCarloEngine()
stress_test = StressTestEngine(bcb_service, tax_calc)
macro_service = MacroScenarioService(market_data.bcb)

analyze_use_case = AnalyzePortfolioUseCase(
    optimizer=None,
    monte_carlo=monte_carlo,
    stress_test=stress_test,
    ai_service=ai_service
)

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# ── helper: build ideal portfolio from markowitz + macro ──

async def _get_ideal_portfolio(profile_type: str, mds: MarketDataService):
    """
    centralized portfolio construction helper.
    uses forward-looking macro data (focus) for expected returns
    and historical data for the covariance matrix.
    returns (weights_dict, optimization_result, historical_data_dict).
    """
    candidate_benchmarks = ["CDI", "IMA-B", "IBOVESPA", "IFIX", "IVVB11", "SMLL", "IRF-M 1"]
    all_hist_data = mds.get_all_benchmarks(candidate_benchmarks, start_year=2023)

    # filter to only benchmarks that returned data
    names = [n for n in candidate_benchmarks if n in all_hist_data and len(all_hist_data[n]) > 0]
    if len(names) < 2:
        logger.warning("_get_ideal_portfolio: insufficient benchmark data, returning empty")
        return {}, None, {}

    # macro projections (cached, fallback-safe)
    macro = macro_service.build_current_scenario()

    # expected returns from focus projections (forward-looking)
    expected_returns = np.array([macro.get_expected_return(b) for b in names])

    # covariance from historical data
    min_len = min(len(all_hist_data[n]) for n in names)
    returns_matrix = np.column_stack([all_hist_data[n][:min_len] for n in names])
    monthly_cov = np.cov(returns_matrix, rowvar=False)
    annual_cov = monthly_cov * 12

    asset_categories = {
        n: "fixed_income" if "CDI" in n or "IMA" in n or "IRF" in n else "equity"
        for n in names
    }

    optimizer = MarkowitzOptimizer(
        asset_names=names,
        expected_returns=expected_returns,
        covariance_matrix=annual_cov,
        asset_categories=asset_categories,
        risk_free_rate=macro.cdi_annual / 100,
    )

    # profile-specific weight constraints
    max_w = {n: 0.80 for n in names}

    if profile_type == "conservative":
        max_w["IBOVESPA"] = 0.03
        max_w["SMLL"] = 0.02
        max_w["IVVB11"] = 0.00
        max_w["IFIX"] = 0.05
        max_w["IMA-B"] = 0.20
    elif profile_type == "aggressive":
        max_w["IBOVESPA"] = 0.50
        max_w["SMLL"] = 0.20
        max_w["IVVB11"] = 0.20
    else:  # moderate (default)
        max_w["IBOVESPA"] = 0.20
        max_w["SMLL"] = 0.10
        max_w["IVVB11"] = 0.10

    # filter max_w to only keys that exist in names
    max_w = {k: v for k, v in max_w.items() if k in names}

    opt_result = optimizer.optimize_max_sharpe(max_weights=max_w)

    weights = {k: float(v) for k, v in opt_result.weights.items() if v > 0.01}
    return weights, opt_result, all_hist_data


# ── helper: build Portfolio entity from weights ──

def _build_portfolio_entity(weights: dict, hist_data: dict, opt_result) -> Portfolio:
    """build a domain Portfolio entity from optimization results."""
    allocations = []
    for bench, weight in weights.items():
        returns = hist_data.get(bench, np.array([]))
        asset = Asset(
            name=bench,
            asset_class=AssetClass.FIXED_INCOME if "CDI" in bench or "IMA" in bench or "IRF" in bench else AssetClass.EQUITY,
            subclass="index",
            benchmark=bench,
            spread=Decimal("0.0"),
            tax_exempt=False,
            min_investment=Decimal("0"),
            liquidity_days=0,
            ticker=bench,
            historical_returns=returns.tolist() if len(returns) > 0 else [],
        )
        allocations.append(PortfolioAllocation(asset=asset, weight=Decimal(str(weight))))

    return Portfolio(
        allocations=allocations,
        expected_return=Decimal(str(opt_result.expected_return)),
        volatility=Decimal(str(opt_result.expected_volatility)),
        sharpe_ratio=Decimal(str(opt_result.sharpe_ratio)),
    )


# ══════════════════════════════════════════════
#  ROUTES
# ══════════════════════════════════════════════

@router.get("/")
async def landing(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})


@router.get("/pricing")
async def pricing(request: Request):
    return templates.TemplateResponse("pricing.html", {"request": request})


@router.get("/dashboard")
async def dashboard(
    request: Request,
    user: DomainUser | None = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if not user:
        return RedirectResponse(url="/login")

    profile_repo = SQLAlchemyProfileRepository(session)
    profile = await profile_repo.get_by_user(user.id)
    plan_display = str(getattr(user, "plan", "free")).split(".")[-1].capitalize()

    if not profile:
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user_name": user.name,
            "user_plan": plan_display,
            "active_page": "dashboard",
            "has_profile": False,
        })

    profile_type = profile.risk_profile.value if hasattr(profile.risk_profile, "value") else str(profile.risk_profile)
    profile_label = PROFILE_LABELS.get(profile_type, profile_type.capitalize())
    initial_amount = float(profile.initial_amount)
    needs_patrimony = initial_amount <= 0

    # 1. get ideal allocation
    weights, opt_result, all_hist_data = await _get_ideal_portfolio(profile_type, market_data)

    if not weights:
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user_name": user.name,
            "user_plan": plan_display,
            "active_page": "dashboard",
            "has_profile": True,
            "needs_patrimony": needs_patrimony,
            "profile_type": profile_label,
            "total_value": f"{initial_amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
            "initial_amount": initial_amount,
            "risk": risk_engine._empty_report("CDI"),
            "analysis": {"backtest": {}, "monte_carlo": {}, "target_weights": {}, "narration": "Dados de mercado indisponíveis no momento."},
            "weights": {},
            "narration": "Dados de mercado indisponíveis no momento.",
        })

    # 2. compute risk metrics
    benchmarks = list(weights.keys())
    hist_data = {b: all_hist_data[b] for b in benchmarks if b in all_hist_data}

    risk_report = risk_engine.compute_portfolio(
        asset_returns=hist_data,
        weights=weights,
        benchmark_name="CDI",
    )

    # 3. build portfolio entity
    portfolio = _build_portfolio_entity(weights, hist_data, opt_result)

    # 4. run full analysis (backtest + monte carlo + ai narration)
    analysis = await analyze_use_case.execute(
        portfolio,
        initial_amount=initial_amount,
        target_weights=weights,
        risk_metrics=risk_report,
        profile_type=profile_label,
    )

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user_name": user.name,
        "user_plan": plan_display,
        "active_page": "dashboard",
        "has_profile": True,
        "needs_patrimony": needs_patrimony,
        "profile_type": profile_label,
        "total_value": f"{initial_amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "initial_amount": initial_amount,
        "risk": risk_report,
        "analysis": analysis,
        "weights": weights,
        "narration": analysis["narration"],
    })


@router.post("/update-patrimony")
async def update_patrimony(
    patrimony: float = Form(...),
    user: DomainUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    profile_repo = SQLAlchemyProfileRepository(session)
    profile = await profile_repo.get_by_user(user.id)
    if profile:
        await session.execute(
            update(ProfileModel)
            .where(ProfileModel.user_id == user.id)
            .values(initial_amount=patrimony)
        )
        await session.commit()
    return RedirectResponse(url="/dashboard", status_code=303)


@router.get("/quiz")
async def quiz(
    request: Request,
    user: DomainUser | None = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    has_existing_profile = False
    if user:
        profile_repo = SQLAlchemyProfileRepository(session)
        profile = await profile_repo.get_by_user(user.id)
        if profile:
            has_existing_profile = True

    questions = quiz_service.get_questions()
    questions_data = []
    for q in questions:
        questions_data.append({
            "id": q.id,
            "text": q.text,
            "section": q.section,
            "options": [{"id": o.id, "text": o.text, "score": o.score} for o in q.options],
        })

    return templates.TemplateResponse("quiz.html", {
        "request": request,
        "questions_json": json.dumps(questions_data),
        "user": user,
        "user_name": user.name if user else None,
        "user_plan": str(getattr(user, "plan", "free")).split(".")[-1].capitalize() if user else "Free",
        "active_page": "quiz",
        "has_existing_profile": has_existing_profile,
    })


@router.get("/simulation")
async def simulation(
    request: Request,
    user: DomainUser | None = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if not user:
        return RedirectResponse(url="/login")

    profile_repo = SQLAlchemyProfileRepository(session)
    profile = await profile_repo.get_by_user(user.id)
    if not profile:
        return RedirectResponse(url="/dashboard")

    initial_amount = float(profile.initial_amount)
    profile_type = profile.risk_profile.value if hasattr(profile.risk_profile, "value") else str(profile.risk_profile)

    # 1. get ideal allocation
    weights_map, opt_result, all_hist_data = await _get_ideal_portfolio(profile_type, market_data)

    if not weights_map or opt_result is None:
        return templates.TemplateResponse("simulation.html", {
            "request": request,
            "user_name": user.name,
            "user_plan": str(getattr(user, "plan", "free")).split(".")[-1].capitalize(),
            "active_page": "simulation",
            "initial_amount": initial_amount,
            "chart_data_json": json.dumps({"labels": [], "p5": [], "p50": [], "p95": []}),
            "results": {"p5": 0, "p50": 0, "p95": 0},
        })

    logger.info(f"--- SIMULATION START ---")
    logger.info(f"Amount: R$ {initial_amount:,.2f} | Profile: {profile_type}")

    # 2. build portfolio entity
    hist_data = {b: all_hist_data[b] for b in weights_map if b in all_hist_data}
    portfolio = _build_portfolio_entity(weights_map, hist_data, opt_result)

    # 3. run monte carlo
    logger.info(f"Running 5,000 stochastic scenarios for {len(portfolio.allocations)} assets...")
    sim_result = monte_carlo.simulate(
        portfolio,
        initial_amount=initial_amount,
        horizon_months=60,
        num_simulations=5000,
        monthly_contribution=float(profile.monthly_contribution),
    )

    p5_path = np.percentile(sim_result.paths, 5, axis=0)
    p50_path = np.percentile(sim_result.paths, 50, axis=0)
    p95_path = np.percentile(sim_result.paths, 95, axis=0)

    logger.info(f"Simulation complete. P5={p5_path[-1]:,.0f} | P50={p50_path[-1]:,.0f} | P95={p95_path[-1]:,.0f}")

    chart_data = {
        "labels": list(range(61)),
        "p5": p5_path.tolist(),
        "p50": p50_path.tolist(),
        "p95": p95_path.tolist(),
    }

    return templates.TemplateResponse("simulation.html", {
        "request": request,
        "user_name": user.name,
        "user_plan": str(getattr(user, "plan", "free")).split(".")[-1].capitalize(),
        "active_page": "simulation",
        "initial_amount": initial_amount,
        "chart_data_json": json.dumps(chart_data),
        "results": {
            "p5": p5_path[-1],
            "p50": p50_path[-1],
            "p95": p95_path[-1],
        },
    })


@router.get("/gap-analysis")
async def gap_analysis(
    request: Request,
    user: DomainUser | None = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if not user:
        return RedirectResponse(url="/login")

    profile_repo = SQLAlchemyProfileRepository(session)
    profile = await profile_repo.get_by_user(user.id)
    if not profile:
        return RedirectResponse(url="/dashboard")

    profile_type = profile.risk_profile.value if hasattr(profile.risk_profile, "value") else str(profile.risk_profile)
    profile_label = PROFILE_LABELS.get(profile_type, profile_type.capitalize())

    # 1. get ideal allocation
    ideal_weights, opt_result, all_hist_data = await _get_ideal_portfolio(profile_type, market_data)

    # 2. placeholder current portfolio (until user imports real holdings)
    current_weights = {"Poupança/CDI": 0.85, "Ações (Varejo)": 0.15}
    current_monthly_return = 0.007  # ~CDI

    # 3. compute gap metrics
    if opt_result is not None:
        ideal_annual = opt_result.expected_return
    else:
        ideal_annual = 0.10  # fallback

    current_annual = (1 + current_monthly_return) ** 12 - 1
    annual_gap = ideal_annual - current_annual
    gain_lost = float(profile.initial_amount) * abs(annual_gap) * 5  # 5-year opportunity cost

    # 4. compute risk report for ai narration (needed by the prompt)
    if ideal_weights and all_hist_data:
        hist_data = {b: all_hist_data[b] for b in ideal_weights if b in all_hist_data}
        risk_report = risk_engine.compute_portfolio(
            asset_returns=hist_data,
            weights=ideal_weights,
            benchmark_name="CDI",
        )
    else:
        risk_report = risk_engine._empty_report("CDI")

    # 5. ai narration
    narration = await ai_service.explain_committee_review(
        ideal_weights,
        risk_report,
        profile_label,
    )

    return templates.TemplateResponse("gap_analysis.html", {
        "request": request,
        "user_name": user.name,
        "user_plan": str(getattr(user, "plan", "free")).split(".")[-1].capitalize(),
        "active_page": "gap_analysis",
        "profile_type": profile_label,
        "ideal_weights": ideal_weights,
        "current_weights": current_weights,
        "current_score": 42.0,
        "ideal_score": profile.score,
        "gain_lost": abs(gain_lost),
        "narration": narration,
    })
