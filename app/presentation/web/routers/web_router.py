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

from ....infrastructure.external.market_data_service import MarketDataService
from ....infrastructure.external.macro_scenario_service import MacroScenarioService
from ....infrastructure.repositories.profile_repository import SQLAlchemyProfileRepository
from ....infrastructure.repositories.user_asset_repository import SQLAlchemyUserAssetRepository
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

    # fetch current assets from database
    asset_repo = SQLAlchemyUserAssetRepository(session)
    user_assets = await asset_repo.list_by_user(user.id)
    
    if user_assets:
        current_weights = {}
        total_current_value = sum(float(a.current_value or (a.quantity * a.average_price)) for a in user_assets)
        if total_current_value > 0:
            for a in user_assets:
                val = float(a.current_value or (a.quantity * a.average_price))
                cls_key = a.asset_class.value
                current_weights[cls_key] = current_weights.get(cls_key, 0.0) + (val / total_current_value)
        else:
            current_weights = {"renda_fixa": 1.0}
            total_current_value = float(profile.initial_amount)
    else:
        # fallback placeholder current portfolio
        current_weights = {"renda_fixa": 0.85, "renda_variavel": 0.15}
        total_current_value = float(profile.initial_amount)

    current_monthly_return = 0.007  # ~cdi baseline for legacy

    # compute gap
    if portfolio is not None:
        ideal_annual = portfolio.weighted_expected_annual_return
        ideal_net_annual = portfolio.expected_net_annual_return(24)
        ideal_allocations = portfolio.get_allocation_summary()
        ideal_class_breakdown = portfolio.get_class_breakdown()
    else:
        ideal_annual = 0.10
        ideal_net_annual = 0.085
        ideal_allocations = []
        ideal_class_breakdown = {}

    # estimate current return from asset classes instead of hardcoded baseline
    _return_by_class = {
        "renda_fixa": 0.1475,       # cdi ≈ selic
        "renda_variavel": 0.14,     # ibovespa rolling avg
        "fii": 0.12,                # ifix avg
        "internacional": 0.15,      # sp500 brl adjusted
        "previdencia": 0.10,
        "alternativo": 0.20,
    }
    current_annual = sum(
        w * _return_by_class.get(cls, 0.10)
        for cls, w in current_weights.items()
    )
    # apply 15% ir on current portfolio (conservative)
    current_net_annual = current_annual * 0.85

    annual_gap = ideal_net_annual - current_net_annual
    gain_lost = total_current_value * abs(annual_gap) * 5  # 5-year opportunity cost

    # build chart json for dual doughnut
    class_labels_pt = {
        "renda_fixa": "Renda Fixa",
        "renda_variavel": "Renda Variável",
        "fii": "FII",
        "internacional": "Internacional",
        "previdencia": "Previdência",
        "alternativo": "Alternativo",
    }
    current_chart = {
        "labels": [class_labels_pt.get(k, k) for k in current_weights],
        "data": [round(v * 100, 1) for v in current_weights.values()],
    }
    ideal_chart = {
        "labels": [class_labels_pt.get(k, k) for k in ideal_class_breakdown],
        "data": [round(v * 100, 1) for v in ideal_class_breakdown.values()],
    }

    # ai narration for gap
    try:
        narration = await ai_service.explain_gap_analysis(
            current_weights=current_weights,
            ideal_allocations=ideal_allocations,
            annual_gap=annual_gap,
            gain_lost=gain_lost,
            profile_label=profile_label,
        )
    except Exception as e:
        logger.warning(f"gap analysis narration failed: {e}")
        narration = ""

    return templates.TemplateResponse("gap_analysis.html", {
        "request": request,
        "user_name": user.name,
        "user_plan": str(getattr(user, "plan", "free")).split(".")[-1].capitalize(),
        "active_page": "gap_analysis",
        "profile_type": profile_label,
        "ideal_allocations": ideal_allocations,
        "current_weights": current_weights,
        "total_current_value": total_current_value,
        "current_annual": current_annual,
        "ideal_annual": ideal_annual,
        "gain_lost": abs(gain_lost),
        "annual_gap": annual_gap,
        "has_real_assets": len(user_assets) > 0,
        "current_chart_json": json.dumps(current_chart),
        "ideal_chart_json": json.dumps(ideal_chart),
        "narration": narration,
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
