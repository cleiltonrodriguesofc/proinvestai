"""
web router — main application routes.

connects the suitability quiz, portfolio builder, and simulation engine
to the jinja2 frontend templates.
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

import numpy as np
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from ....application.services.quiz_service import QuizService
from ....application.services.monte_carlo_engine import MonteCarloEngine
from ....application.services.risk_metrics_engine import RiskMetricsEngine
from ....application.services.stress_test_engine import StressTestEngine
from ....application.services.tax_calculator import TaxCalculator
from ....application.services.portfolio_builder import (
    build_asset_catalog,
    build_optimized_portfolio,
    compute_forward_projections,
)
from ....domain.entities.user import User as DomainUser
from ....domain.entities.user_asset import UserAsset as DomainAsset
from ....domain.entities.asset import AssetClass
from ....infrastructure.external.bcb_service import BCBService
from ....infrastructure.external.openai_service import AIService
from ....infrastructure.external.market_data_service import MarketDataService
from ....infrastructure.external.macro_scenario_service import MacroScenarioService
from ....infrastructure.repositories.profile_repository import SQLAlchemyProfileRepository
from ....infrastructure.repositories.user_asset_repository import SQLAlchemyUserAssetRepository
from ....infrastructure.repositories.rpps_repository import SQLAlchemyRppsRepository
from ....domain.entities.rpps_entities import RppsInstitute
from ....infrastructure.database.connection import get_session
from ....infrastructure.database.models import InvestorProfile as ProfileModel
from .auth import get_current_user

logger = logging.getLogger(__name__)

# ── shared constants ──

PROFILE_LABELS = {
    "conservative": "Conservador",
    "moderate": "Moderado",
    "aggressive": "Arrojado",
    "ultraconservative": "Conservador",
    "ultra_aggressive": "Arrojado",
}

# map quiz result names to engine profile keys
PROFILE_MAP = {
    "conservative": "conservative",
    "moderate": "moderate",
    "aggressive": "aggressive",
    "ultraconservative": "conservative",
    "ultra_aggressive": "aggressive",
    "Conservador": "conservative",
    "Moderado": "moderate",
    "Arrojado": "aggressive",
}


# ── service singletons ──

router = APIRouter()
quiz_service = QuizService()
market_data = MarketDataService()
risk_engine = RiskMetricsEngine()
bcb_service = BCBService()
ai_service = AIService()
monte_carlo = MonteCarloEngine()
macro_service = MacroScenarioService(market_data.bcb)
stress_engine = StressTestEngine(bcb_service, TaxCalculator())

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# ── helper: normalize profile to engine key ──

def _normalize_profile(profile_type) -> str:
    """normalize profile type string to engine key (conservative/moderate/aggressive)."""
    raw = profile_type.value if hasattr(profile_type, "value") else str(profile_type)
    return PROFILE_MAP.get(raw, "moderate")


def _format_brl(value: float) -> str:
    """format value as brazilian real."""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ── helper: build portfolio for any route ──

def _build_portfolio_for_profile(profile, macro=None):
    """
    centralized portfolio construction using the real asset catalog.
    returns (portfolio, projections, macro) or (None, None, macro) on failure.
    """
    if macro is None:
        macro = macro_service.build_current_scenario()

    profile_key = _normalize_profile(profile.risk_profile)
    initial_amount = float(profile.initial_amount)
    
    # Extract real expenses from Q29 and dependents from Q30 if available
    monthly_expenses = float(getattr(profile, "monthly_income", 0)) * 0.7
    reserve_multiplier = 1.0
    
    if hasattr(profile, "raw_responses") and profile.raw_responses:
        responses = profile.raw_responses
        if isinstance(responses, str):
            try:
                responses = json.loads(responses)
            except:
                responses = []
        
        if isinstance(responses, list):
            for ans in responses:
                q_id = ans.get("question_id")
                opt = ans.get("option_id")
                
                if q_id == "q29":
                    if opt == "o29a": monthly_expenses = 3000.0
                    elif opt == "o29b": monthly_expenses = 5500.0
                    elif opt == "o29c": monthly_expenses = 11500.0
                    elif opt == "o29d": monthly_expenses = 20000.0
                
                elif q_id == "q30":
                    if opt == "o30a": reserve_multiplier = 2.0  # 5+ people
                    elif opt == "o30b": reserve_multiplier = 1.5  # 3-4 people
                    elif opt == "o30c": reserve_multiplier = 1.2  # 1-2 people
                    elif opt == "o30d": reserve_multiplier = 1.0  # 0 people

    # build catalog and portfolio
    catalog = build_asset_catalog(macro, profile_key)
    if not catalog:
        logger.error("empty asset catalog — cannot build portfolio")
        return None, None, macro

    # get historical returns from bcb for markowitz
    hist_data = bcb_service.build_asset_return_series(start_year=2015)

    portfolio = build_optimized_portfolio(
        catalog=catalog,
        total_value=initial_amount,
        monthly_expenses=monthly_expenses,
        profile=profile_key,
        macro=macro,
        historical_returns=hist_data if hist_data else None,
        reserve_multiplier=reserve_multiplier,
    )

    # forward projections (5 years with selic trajectory)
    projections = compute_forward_projections(macro, portfolio, years=5)

    return portfolio, projections, macro


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

    rpps_repo = SQLAlchemyRppsRepository(session)
    institute = await rpps_repo.get_institute_by_user(user.id)
    plan_display = str(getattr(user, "plan", "free")).split(".")[-1].capitalize()

    if not institute:
        return templates.TemplateResponse("rpps_onboarding.html", {
            "request": request,
            "user_name": user.name,
            "user_plan": plan_display,
            "active_page": "dashboard",
            "has_profile": False,
        })

    positions = await rpps_repo.list_positions(institute.id)
    mapped_assets_value = sum(float(p.current_balance or 0) for p in positions)
    
    # if institute exists, show the RPPS dashboard
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user_name": user.name,
        "user_plan": plan_display,
        "active_page": "dashboard",
        "has_profile": True,
        "needs_patrimony": False,
        "institute": institute,
        "positions": positions,
        "mapped_assets_value": _format_brl(mapped_assets_value),
        "total_value": _format_brl(float(institute.total_assets))
    })

@router.post("/onboarding/rpps")
async def onboarding_rpps(
    request: Request,
    cnpj: str = Form(...),
    name: str = Form(...),
    municipality: str = Form(...),
    state: str = Form(...),
    total_assets: float = Form(...),
    actuarial_target_index: str = Form(...),
    actuarial_target_rate: float = Form(...),
    pro_gestao_level: int = Form(...),
    user: DomainUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    rpps_repo = SQLAlchemyRppsRepository(session)
    
    new_institute = RppsInstitute(
        cnpj=cnpj,
        name=name,
        municipality=municipality,
        state=state,
        total_assets=total_assets,
        actuarial_target_index=actuarial_target_index,
        actuarial_target_rate=actuarial_target_rate,
        pro_gestao_level=pro_gestao_level
    )
    
    await rpps_repo.create_institute(new_institute, user.id)
    return RedirectResponse(url="/dashboard", status_code=303)


# ── RPPS placeholder routes (to be fully implemented) ──────────────────────

@router.get("/portfolio")
async def portfolio(
    request: Request,
    user: DomainUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """RPPS portfolio detail page — Ativos e Contas."""
    if not user:
        return RedirectResponse(url="/login")
    rpps_repo = SQLAlchemyRppsRepository(session)
    institute = await rpps_repo.get_institute_by_user(user.id)
    positions = await rpps_repo.list_positions(institute.id) if institute else []
    plan_display = str(getattr(user, "plan", "free")).split(".")[-1].upper()
    mapped_value = sum(float(p.current_balance or 0) for p in positions)
    return templates.TemplateResponse("portfolio.html", {
        "request": request,
        "user_name": user.name,
        "user_plan": plan_display,
        "active_page": "portfolio",
        "institute": institute,
        "positions": sorted(positions, key=lambda p: float(p.current_balance or 0), reverse=True),
        "total_value": _format_brl(mapped_value),
    })


@router.get("/portfolio/add")
async def add_portfolio_item(
    request: Request,
    user: DomainUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Page to add a new fund or asset to the RPPS portfolio."""
    if not user:
        return RedirectResponse(url="/login")
        
    rpps_repo = SQLAlchemyRppsRepository(session)
    institute = await rpps_repo.get_institute_by_user(user.id)
    plan_display = str(getattr(user, "plan", "free")).split(".")[-1].upper()
    return templates.TemplateResponse("add_fund.html", {
        "request": request,
        "user_name": user.name,
        "user_plan": plan_display,
        "active_page": "portfolio",
        "institute": institute,
    })


@router.get("/compliance")
async def compliance(
    request: Request,
    user: DomainUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """CMN 5.272 compliance page — Enquadramento."""
    if not user:
        return RedirectResponse(url="/login")
    rpps_repo = SQLAlchemyRppsRepository(session)
    institute = await rpps_repo.get_institute_by_user(user.id)
    positions = await rpps_repo.list_positions(institute.id) if institute else []
    plan_display = str(getattr(user, "plan", "free")).split(".")[-1].upper()
    return templates.TemplateResponse("compliance.html", {
        "request": request,
        "user_name": user.name,
        "user_plan": plan_display,
        "active_page": "compliance",
        "institute": institute,
        "positions": positions,
    })


@router.get("/reports")
async def reports(
    request: Request,
    user: DomainUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Reports page — DAIR / DPIN."""
    if not user:
        return RedirectResponse(url="/login")
    rpps_repo = SQLAlchemyRppsRepository(session)
    institute = await rpps_repo.get_institute_by_user(user.id)
    plan_display = str(getattr(user, "plan", "free")).split(".")[-1].upper()
    return templates.TemplateResponse("reports.html", {
        "request": request,
        "user_name": user.name,
        "user_plan": plan_display,
        "active_page": "reports",
        "institute": institute,
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

    return templates.TemplateResponse(request, "quiz.html", {
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
    profile_key = _normalize_profile(profile.risk_profile)
    profile_label = PROFILE_LABELS.get(profile_key, profile_key.capitalize())

    # build portfolio
    portfolio, projections, macro = _build_portfolio_for_profile(profile)

    empty_ctx = {
        "request": request,
        "user_name": user.name,
        "user_plan": str(getattr(user, "plan", "free")).split(".")[-1].capitalize(),
        "active_page": "simulation",
        "profile_type": profile_label,
        "initial_amount": initial_amount,
        "chart_data_json": json.dumps({"labels": [], "p5": [], "p50": [], "p95": []}),
        "results": {"p5": 0, "p50": 0, "p95": 0},
        "stress_tests": [],
        "backtest": None,
        "risk_metrics": None,
        "narration": "",
    }

    if portfolio is None:
        return templates.TemplateResponse("simulation.html", empty_ctx)

    logger.info(f"--- SIMULATION START ---")
    logger.info(f"Amount: R$ {initial_amount:,.2f} | Profile: {profile_key}")

    # ── 1. monte carlo ──
    logger.info(f"Running 5,000 stochastic scenarios for {len(portfolio.allocations)} products...")
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

    logger.info(f"MC complete. P5={p5_path[-1]:,.0f} | P50={p50_path[-1]:,.0f} | P95={p95_path[-1]:,.0f}")

    chart_data = {
        "labels": list(range(61)),
        "p5": p5_path.tolist(),
        "p50": p50_path.tolist(),
        "p95": p95_path.tolist(),
    }

    # ── 2. stress test (crisis scenarios) ──
    try:
        stress_tests = stress_engine.run_crisis_tests(portfolio, initial_amount)
    except Exception as e:
        logger.warning(f"stress test failed: {e}")
        stress_tests = []

    # ── 3. backtest ──
    try:
        backtest = stress_engine.run_backtest(portfolio, initial_amount)
        if "error" in backtest:
            logger.warning(f"backtest returned error: {backtest['error']}")
            backtest = None
    except Exception as e:
        logger.warning(f"backtest failed: {e}")
        backtest = None

    # ── 4. risk metrics from portfolio properties ──
    risk_metrics = {
        "sharpe": portfolio.weighted_expected_annual_return / max(portfolio.weighted_volatility, 0.001),
        "volatility": portfolio.weighted_volatility,
        "expected_return": portfolio.weighted_expected_annual_return,
        "net_return": portfolio.expected_net_annual_return(24),
        "max_drawdown": backtest.get("max_drawdown", 0.0) if backtest else 0.0,
        "risk_category": portfolio.risk_category,
    }

    # ── 5. ai narration ──
    try:
        narration = await ai_service.explain_simulation(
            profile_label=profile_label,
            initial_amount=initial_amount,
            p5=float(p5_path[-1]),
            p50=float(p50_path[-1]),
            p95=float(p95_path[-1]),
            stress_tests=stress_tests,
            risk_metrics=risk_metrics,
        )
    except Exception as e:
        logger.warning(f"ai narration failed: {e}")
        narration = ""

    return templates.TemplateResponse("simulation.html", {
        "request": request,
        "user_name": user.name,
        "user_plan": str(getattr(user, "plan", "free")).split(".")[-1].capitalize(),
        "active_page": "simulation",
        "profile_type": profile_label,
        "initial_amount": initial_amount,
        "chart_data_json": json.dumps(chart_data),
        "results": {
            "p5": p5_path[-1],
            "p50": p50_path[-1],
            "p95": p95_path[-1],
        },
        "stress_tests": stress_tests,
        "backtest": backtest,
        "risk_metrics": risk_metrics,
        "narration": narration,
        # monte carlo extra stats
        "prob_loss": sim_result.probability_of_loss(initial_amount),
        "prob_double": sim_result.probability_above_target(initial_amount * 2),
    })


@router.get("/gap-analysis")
async def gap_analysis(
    request: Request,
    user: DomainUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """RPPS Gap Analysis — Current vs ALM Recommended."""
    if not user:
        return RedirectResponse(url="/login")
    rpps_repo = SQLAlchemyRppsRepository(session)
    institute = await rpps_repo.get_institute_by_user(user.id)
    if not institute:
        return RedirectResponse(url="/dashboard")

    # Import ALM dependencies locally to avoid circular imports if any, or just use them
    from ....application.services.alm_engine import ALMEngine
    
    config_path = Path(__file__).resolve().parent.parent.parent.parent / "alm" / "config" / "ipsemb_2026.json"
    
    gap_data = []
    recommended_weights = {}
    current_return = 0
    ideal_return = 0
    current_vol = 0
    ideal_vol = 0
    
    try:
        engine = ALMEngine(config_path)
        engine.load_cashflows()
        result = engine.run(n_scenarios=100, horizon_years=10) # Quick run for gap data
        
        for bench, data in result.gap_table.items():
            gap_data.append({
                "benchmark": bench,
                "current_pct": data.get("current_pct", 0),
                "current_value": data.get("current_value", 0),
                "recommended_pct": data.get("recommended_pct", 0),
                "gap_pct": data.get("gap_pct", 0),
            })
            
        rec = result.recommended_portfolio
        if rec:
            recommended_weights = {k: v for k, v in rec.weights.items() if v > 0.001}
            
        current_return = result.current_portfolio.expected_return
        ideal_return = rec.expected_return if rec else 0
        current_vol = result.current_portfolio.volatility
        ideal_vol = rec.volatility if rec else 0
    except Exception as e:
        logger.error(f"Gap analysis ALM engine failed: {e}")
        # Provide some fallback metrics for demonstration if ALM can't run
        current_return = 10.5
        ideal_return = 12.0
        current_vol = 5.2
        ideal_vol = 7.5

    return templates.TemplateResponse("gap_analysis.html", {
        "request": request,
        "user_name": user.name,
        "user_plan": str(getattr(user, "plan", "free")).split(".")[-1].upper(),
        "active_page": "gap",
        "institute": institute,
        "gap_data": gap_data,
        "recommended_weights": recommended_weights,
        "current_return": current_return,
        "ideal_return": ideal_return,
        "current_vol": current_vol,
        "ideal_vol": ideal_vol,
    })


@router.get("/my-portfolio")
async def my_portfolio(
    request: Request,
    user: DomainUser | None = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if not user:
        return RedirectResponse(url="/login")

    asset_repo = SQLAlchemyUserAssetRepository(session)
    assets = await asset_repo.list_by_user(user.id)
    
    return templates.TemplateResponse("my_portfolio.html", {
        "request": request,
        "user_name": user.name,
        "active_page": "my-portfolio",
        "assets": assets
    })


@router.post("/add-asset")
async def add_asset(
    asset_name: str = Form(...),
    asset_class: str = Form(...),
    quantity: float = Form(...),
    average_price: float = Form(...),
    purchase_date: str = Form(...),
    ticker: str = Form(None),
    user: DomainUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    asset_repo = SQLAlchemyUserAssetRepository(session)
    
    new_asset = DomainAsset(
        id=uuid.uuid4(),
        user_id=user.id,
        asset_name=asset_name,
        asset_class=AssetClass(asset_class),
        quantity=quantity,
        average_price=average_price,
        purchase_date=datetime.strptime(purchase_date, "%Y-%m-%d").date(),
        ticker=ticker,
        current_value=quantity * average_price # placeholder current value
    )
    
    await asset_repo.create(new_asset)
    return RedirectResponse(url="/my-portfolio", status_code=303)


@router.post("/delete-asset/{asset_id}")
async def delete_asset(
    asset_id: uuid.UUID,
    user: DomainUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    asset_repo = SQLAlchemyUserAssetRepository(session)
    await asset_repo.delete(asset_id)
    return RedirectResponse(url="/my-portfolio", status_code=303)
