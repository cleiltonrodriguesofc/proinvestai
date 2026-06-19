"""
alm router — asset-liability management dashboard.

standalone section for rpps alm studies. not part of the main
authenticated app — designed as a configurable analysis tool
for comparing alm outputs with external consultants (lema).
"""

import json
import logging
from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ....application.services.alm_engine import (
    ALMEngine,
    project_patrimony,
)
from ....application.services.actuarial_flow_parser import get_flow_summary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alm", tags=["alm"])

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# default config path (can be overridden via query param)
DEFAULT_CONFIG = Path(__file__).resolve().parent.parent.parent.parent / "alm" / "config" / "ipsemb_2026.json"


def _format_brl(value: float) -> str:
    """format value as brazilian real."""
    if abs(value) >= 1_000_000:
        return f"R$ {value/1_000_000:,.1f}M".replace(",", "X").replace(".", ",").replace("X", ".")
    if abs(value) >= 1_000:
        return f"R$ {value/1_000:,.1f}K".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _format_brl_full(value: float) -> str:
    """format value as full brazilian real."""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _build_alm_context(
    request: Request,
    config: str,
    scenarios: int,
    horizon: int,
):
    """main alm dashboard — runs full study and renders results."""
    config_path = Path(config) if config else DEFAULT_CONFIG

    try:
        engine = ALMEngine(config_path)
        engine.load_cashflows()
        result = engine.run(n_scenarios=scenarios, horizon_years=horizon)
    except Exception as e:
        logger.error(f"alm engine failed: {e}", exc_info=True)
        return templates.TemplateResponse("alm_dashboard.html", {
            "request": request,
            "error": str(e),
        })

    # flow summary
    flow_summary = get_flow_summary(result.cashflows)

    # cashflow chart (full horizon up to 75 years)
    cf_horizon = min(75, len(result.cashflows))

    # patrimony projection with required return
    patrimony_projection = project_patrimony(
        result.cashflows[:cf_horizon],
        result.patrimony,
        result.required_return / 100,
    )

    # patrimony projection with actuarial rate (for comparison)
    patrimony_projection_meta = project_patrimony(
        result.cashflows[:cf_horizon],
        result.patrimony,
        result.actuarial_rate / 100,
    )

    # build chart data
    projection_years = [p["year"] for p in patrimony_projection]
    projection_patrimony_eq = [p["projected_patrimony"] for p in patrimony_projection]
    projection_patrimony_meta = [p["projected_patrimony"] for p in patrimony_projection_meta]
    projection_revenues = [p["revenues"] for p in patrimony_projection]
    projection_expenditures = [p["expenditures"] for p in patrimony_projection]
    projection_net_flow = [p["flow_without_investments"] for p in patrimony_projection]

    # cashflow chart (full horizon up to 75 years)
    cf_years = [cf.year for cf in result.cashflows[:cf_horizon]]
    cf_revenues = [cf.total_revenues for cf in result.cashflows[:cf_horizon]]
    cf_expenditures = [cf.total_expenditures for cf in result.cashflows[:cf_horizon]]
    cf_net = [cf.net_flow for cf in result.cashflows[:cf_horizon]]

    # calculate ruin year (when patrimony drops below zero under meta atuarial)
    ruin_year = "Não Zera (Sustentável)"
    for p in patrimony_projection_meta:
        if p["projected_patrimony"] <= 0:
            ruin_year = str(p["year"])
            break

    # portfolio breakdown
    segment_data = result.current_portfolio.segment_breakdown
    benchmark_data = result.current_portfolio.benchmark_breakdown

    # solvency data
    sr = result.solvency_results[0] if result.solvency_results else None
    solvency_years = projection_years[:len(sr.yearly_median_patrimony)] if sr else []
    solvency_patrimony = sr.yearly_median_patrimony if sr else []
    solvency_fr = sr.yearly_median_funding_ratio if sr else []

    # bond allocations
    bond_data = []
    for ba in result.bond_allocations:
        bond_data.append({
            "period": ba.period,
            "bond": ba.bond_name,
            "pv": _format_brl_full(abs(ba.pv_flows)),
            "weight_port": f"{ba.weight_portfolio*100:.1f}%",
            "weight_total": f"{ba.weight_total*100:.1f}%",
            "rate": f"{ba.rate}%",
        })

    # indices table
    indices_data = []
    for idx in result.indices:
        indices_data.append({
            "name": idx.name,
            "segment": idx.segment.value.replace("_", " ").title(),
            "return": f"{idx.projected_real_return:.2f}%",
            "volatility": f"{idx.volatility:.2f}%",
            "model": idx.projection_model.value.replace("_", " ").title(),
        })

    # holdings table
    holdings_data = []
    for h in result.current_portfolio.holdings:
        holdings_data.append({
            "name": h.fund_name,
            "balance": _format_brl_full(h.balance),
            "weight": f"{h.weight:.2f}%",
            "benchmark": h.benchmark,
            "article": h.regulatory_article.value,
            "segment": h.segment.value.replace("_", " ").title(),
            "liquidity": f"D+{h.liquidity_days}",
            "admin_fee": f"{h.admin_fee:.2f}%",
            "monthly_return": f"{h.monthly_return:+.2f}%",
            "is_legacy": h.is_legacy,
        })

    # efficient frontier (10 portfolios)
    frontier_data = []
    for p in result.efficient_frontier:
        frontier_data.append({
            "id": p.portfolio_id,
            "return": p.expected_return,
            "volatility": p.volatility,
            "sharpe": p.sharpe_ratio,
            "weights": {k: round(v * 100, 1) for k, v in p.weights.items() if v > 0.005},
        })

    rec = result.recommended_portfolio
    recommended_data = None
    if rec:
        recommended_data = {
            "id": rec.portfolio_id,
            "return": rec.expected_return,
            "volatility": rec.volatility,
            "sharpe": rec.sharpe_ratio,
            "weights": {k: round(v * 100, 1) for k, v in sorted(rec.weights.items(), key=lambda x: -x[1]) if v > 0.005},
        }

    # gap table (current vs recommended)
    gap_data = []
    for bench, data in result.gap_table.items():
        gap_data.append({
            "benchmark": bench,
            "current_pct": f"{data['current_pct']:.1f}%",
            "current_value": _format_brl(data["current_value"]),
            "recommended_pct": f"{data.get('recommended_pct', 0):.1f}%",
            "gap_pct": f"{data.get('gap_pct', 0):+.1f}%",
        })

    ctx = {
        "request": request,
        "error": None,

        # metadata
        "rpps_name": result.rpps_name,
        "reference_date": result.reference_date,
        "actuarial_rate": result.actuarial_rate,
        "n_scenarios": scenarios,
        "horizon": horizon,

        # headline metrics
        "patrimony": _format_brl_full(result.patrimony),
        "patrimony_raw": result.patrimony,
        "required_return": result.required_return,
        "meta_atuarial": result.meta_atuarial,
        "npv_deficit": _format_brl_full(result.npv_deficit_flows),

        # flow summary
        "flow_summary": flow_summary,
        "first_deficit_year": flow_summary.get("first_deficit_year", "N/A"),
        "ruin_year": ruin_year,

        # actuarial data from config
        "actuarial_data": engine.config.get("actuarial_data", {}),
        "pro_gestao": engine.config.get("pro_gestao_level"),

        # chart data (json)
        "cf_chart_json": json.dumps({
            "years": cf_years,
            "revenues": cf_revenues,
            "expenditures": cf_expenditures,
            "net": cf_net,
        }),
        "projection_chart_json": json.dumps({
            "years": projection_years,
            "patrimony_eq": projection_patrimony_eq,
            "patrimony_meta": projection_patrimony_meta,
            "revenues": projection_revenues,
            "expenditures": projection_expenditures,
        }),
        "solvency_chart_json": json.dumps({
            "years": solvency_years,
            "patrimony": solvency_patrimony,
            "funding_ratio": solvency_fr,
        }),
        
        # new charts for LEMA format
        "scatter_json": json.dumps([
            {
                "label": idx.name,
                "x": idx.volatility,
                "y": idx.projected_real_return,
                "type": "index"
            } for idx in result.indices
        ] + [
            {
                "label": f"Portfólio {p.portfolio_id}",
                "x": p.volatility,
                "y": p.expected_return,
                "type": "portfolio"
            } for p in result.efficient_frontier
        ]),
        
        "stacked_bar_json": json.dumps([
            {
                "label": f"Port. {p.portfolio_id}",
                "weights": p.weights
            } for p in result.efficient_frontier
        ]),
        
        "solvency_results_table": [
            {
                "portfolio_id": sr.portfolio_id,
                "pct_solvent": f"{sr.pct_solvent:.1f}%",
                "mean_funding_ratio": f"{sr.mean_funding_ratio:.2f}",
                "quantile_5": f"{sr.quantile_5_funding_ratio:.2f}"
            }
            for sr in result.solvency_results
        ],

        # full tables for report
        "cashflows_table": [
            {
                "year": cf.year,
                "revenues": _format_brl(cf.total_revenues),
                "expenditures": _format_brl(cf.total_expenditures),
                "net_flow": _format_brl(cf.net_flow),
                "is_deficit": cf.net_flow < 0
            }
            for cf in result.cashflows[:cf_horizon]
        ],
        "projection_table": [
            {
                "year": p["year"],
                "revenues": _format_brl(p["revenues"]),
                "expenditures": _format_brl(p["expenditures"]),
                "net_flow": _format_brl(p["flow_without_investments"]),
                "inv_return_eq": _format_brl(p["investment_result"]),
                "annual_flow_eq": _format_brl(p["annual_flow"]),
                "patrimony_eq": _format_brl(p["projected_patrimony"]),
            }
            for p in patrimony_projection
        ],

        # tables
        "holdings": holdings_data,
        "indices": indices_data,
        "bonds": bond_data,
        "gap": gap_data,
        "frontier": frontier_data,
        "recommended": recommended_data,

        # frontier chart data
        "frontier_chart_json": json.dumps({
            "portfolios": [{"id": p["id"], "ret": p["return"], "vol": p["volatility"], "sharpe": p["sharpe"]} for p in frontier_data],
            "recommended_id": recommended_data["id"] if recommended_data else None,
        }),

        # segment/benchmark breakdowns
        "segment_data": segment_data,
        "segment_json": json.dumps({
            "labels": [k.replace("_", " ").title() for k in segment_data.keys()],
            "values": list(segment_data.values()),
        }),
        "benchmark_json": json.dumps({
            "labels": list(benchmark_data.keys()),
            "values": list(benchmark_data.values()),
        }),

        # solvency stats
        "solvency": {
            "pct_solvent": sr.pct_solvent if sr else 0,
            "mean_fr": sr.mean_funding_ratio if sr else 0,
            "q5_fr": sr.quantile_5_funding_ratio if sr else 0,
            "pct_positive": sr.pct_positive_returns if sr else 0,
            "mean_return": sr.mean_return if sr else 0,
            "min_return": sr.min_return if sr else 0,
            "max_return": sr.max_return if sr else 0,
        },

        # helpers
        "format_brl": _format_brl,
        "format_brl_full": _format_brl_full,
    }

    return ctx


@router.get("")
async def alm_dashboard(
    request: Request,
    config: str = Query(default=None, description="path to config json"),
    scenarios: int = Query(default=1000, ge=100, le=10000),
    horizon: int = Query(default=30, ge=10, le=75),
):
    """main alm dashboard — runs full study and renders results."""
    ctx = _build_alm_context(request, config, scenarios, horizon)
    if not isinstance(ctx, dict):
        return ctx  # already a TemplateResponse with error
    return templates.TemplateResponse("alm_dashboard.html", ctx)


@router.get("/report")
async def alm_report(
    request: Request,
    config: str = Query(default=None, description="path to config json"),
    scenarios: int = Query(default=1000, ge=100, le=10000),
    horizon: int = Query(default=30, ge=10, le=75),
):
    """printable slide-style pdf report of the alm study."""
    ctx = _build_alm_context(request, config, scenarios, horizon)
    if not isinstance(ctx, dict):
        return ctx  # already a TemplateResponse with error
    return templates.TemplateResponse("alm_report.html", ctx)


@router.get("/lema-2025", response_class=HTMLResponse)
async def alm_lema_2025(request: Request):
    """dashboard for lema 2025 validation."""
    ctx = _build_alm_context(request, "app/alm/config/ipsemb_2025_lema.json", 1000, 75)
    if not isinstance(ctx, dict):
        return ctx  # return the TemplateResponse with the error
    if "error" in ctx and ctx["error"]:
        return HTMLResponse(content=f"<h3>Erro: {ctx['error']}</h3>", status_code=500)
    return templates.TemplateResponse("alm_dashboard.html", ctx)


@router.get("/lema-2025/report", response_class=HTMLResponse)
async def alm_lema_2025_report(request: Request):
    """institutional report for lema 2025 validation."""
    ctx = _build_alm_context(request, "app/alm/config/ipsemb_2025_lema.json", 1000, 75)
    if not isinstance(ctx, dict):
        return ctx  # return the TemplateResponse with the error
    if "error" in ctx and ctx["error"]:
        return HTMLResponse(content=f"<h3>Erro: {ctx['error']}</h3>", status_code=500)
    return templates.TemplateResponse("alm_report_lema.html", ctx)


