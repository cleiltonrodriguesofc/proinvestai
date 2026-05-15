"""
web router — main application routes.

connects the suitability quiz, portfolio builder, and simulation engine
to the jinja2 frontend templates.
"""

import json
import logging
import numpy as np
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from ....application.services.quiz_service import QuizService
from ....application.services.monte_carlo_engine import MonteCarloEngine
from ....application.services.risk_metrics_engine import RiskMetricsEngine
from ....application.services.portfolio_builder import (
    build_asset_catalog,
    build_optimized_portfolio,
    compute_forward_projections,
)
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

    profile_key = _normalize_profile(profile.risk_profile)
    profile_label = PROFILE_LABELS.get(profile_key, profile_key.capitalize())
    initial_amount = float(profile.initial_amount)
    needs_patrimony = initial_amount <= 0

    if needs_patrimony:
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user_name": user.name,
            "user_plan": plan_display,
            "active_page": "dashboard",
            "has_profile": True,
            "needs_patrimony": True,
            "profile_type": profile_label,
        })

    # build the real portfolio
    portfolio, projections, macro = _build_portfolio_for_profile(profile)

    if portfolio is None:
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user_name": user.name,
            "user_plan": plan_display,
            "active_page": "dashboard",
            "has_profile": True,
            "needs_patrimony": False,
            "profile_type": profile_label,
            "total_value": _format_brl(initial_amount),
            "error_message": "Dados de mercado indisponiveis no momento. Tente novamente em alguns minutos.",
        })

    # allocation data for frontend
    allocation_summary = portfolio.get_allocation_summary()
    class_breakdown = portfolio.get_class_breakdown()
    validation_issues = portfolio.validate()

    # generate ai narration
    narration = await ai_service.explain_portfolio_recommendation(
        allocation_summary=allocation_summary,
        profile_label=profile_label,
        total_value=initial_amount,
        net_monthly_income=portfolio.expected_net_monthly_income(24),
        gross_annual_return=portfolio.weighted_expected_annual_return,
        net_annual_return=portfolio.expected_net_annual_return(24),
        reserve_months=portfolio.reserve_coverage_months,
        risk_category=portfolio.risk_category,
    )

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user_name": user.name,
        "user_plan": plan_display,
        "active_page": "dashboard",
        "has_profile": True,
        "needs_patrimony": False,
        "profile_type": profile_label,
        "total_value": _format_brl(initial_amount),
        "initial_amount": initial_amount,
        # portfolio data
        "portfolio": portfolio,
        "allocations": allocation_summary,
        "allocations_json": json.dumps(allocation_summary, default=str),
        "class_breakdown": class_breakdown,
        "class_breakdown_json": json.dumps(class_breakdown),
        "projections": projections,
        "projections_json": json.dumps(projections),
        # headline metrics
        "gross_annual_return": portfolio.weighted_expected_annual_return,
        "net_annual_return": portfolio.expected_net_annual_return(24),
        "net_monthly_income": portfolio.expected_net_monthly_income(24),
        "net_monthly_income_display": _format_brl(portfolio.expected_net_monthly_income(24)),
        "liquid_pct": portfolio.liquid_percentage,
        "liquid_value": portfolio.liquid_value,
        "reserve_months_actual": portfolio.reserve_coverage_months,
        "variable_income_pct": portfolio.variable_income_percentage,
        "fgc_protected": portfolio.fgc_protected_value,
        "tax_exempt_pct": portfolio.tax_exempt_percentage,
        "risk_category": portfolio.risk_category,
        "volatility": portfolio.weighted_volatility,
        "validation_issues": validation_issues,
        # ai
        "narration": narration,
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

    # build portfolio
    portfolio, projections, macro = _build_portfolio_for_profile(profile)

    if portfolio is None:
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
    logger.info(f"Amount: R$ {initial_amount:,.2f} | Profile: {_normalize_profile(profile.risk_profile)}")

    # run monte carlo using the real portfolio
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

    profile_key = _normalize_profile(profile.risk_profile)
    profile_label = PROFILE_LABELS.get(profile_key, profile_key.capitalize())

    # build ideal portfolio
    portfolio, projections, macro = _build_portfolio_for_profile(profile)

    # placeholder current portfolio (until user imports real holdings)
    current_weights = {"Poupanca": 0.85, "Acoes (Varejo)": 0.15}
    current_monthly_return = 0.007  # ~cdi

    # compute gap
    if portfolio is not None:
        ideal_annual = portfolio.weighted_expected_annual_return
        ideal_net_annual = portfolio.expected_net_annual_return(24)
        ideal_allocations = portfolio.get_allocation_summary()
    else:
        ideal_annual = 0.10
        ideal_net_annual = 0.085
        ideal_allocations = []

    current_annual = (1 + current_monthly_return) ** 12 - 1
    annual_gap = ideal_net_annual - current_annual
    gain_lost = float(profile.initial_amount) * abs(annual_gap) * 5  # 5-year opportunity cost

    # ai narration for gap
    narration = await ai_service.explain_gap_analysis(
        current_weights=current_weights,
        ideal_allocations=ideal_allocations,
        annual_gap=annual_gap,
        gain_lost=gain_lost,
        profile_label=profile_label,
    )

    return templates.TemplateResponse("gap_analysis.html", {
        "request": request,
        "user_name": user.name,
        "user_plan": str(getattr(user, "plan", "free")).split(".")[-1].capitalize(),
        "active_page": "gap_analysis",
        "profile_type": profile_label,
        "ideal_allocations": ideal_allocations,
        "current_weights": current_weights,
        "current_score": 42.0,
        "ideal_score": profile.score,
        "gain_lost": abs(gain_lost),
        "annual_gap": annual_gap,
        "narration": narration,
    })
