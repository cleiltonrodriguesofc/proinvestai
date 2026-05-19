"""
alm engine — main orchestrator for asset-liability management studies.

replicates the methodology used by lema economia & finanças:
1. parse actuarial flow (cadprev csv)
2. calculate required return (taxa de equilíbrio)
3. project patrimony with investment returns
4. markowitz optimization with cmn 5.272/2025 constraints
5. ntn-b liability matching
6. monte carlo solvency analysis (1000 scenarios)
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

from app.domain.entities.alm_entities import (
    ALMResult,
    AssetIndex,
    AssetSegment,
    BondAllocation,
    CashFlowYear,
    CurrentPortfolio,
    OptimizedPortfolio,
    PortfolioHolding,
    ProjectionModel,
    RegulatoryArticle,
    SolvencyResult,
)
from app.application.services.actuarial_flow_parser import (
    parse_cadprev_csv,
    get_flow_summary,
)


# ---------------------------------------------------------------------------
# config loader
# ---------------------------------------------------------------------------

def load_alm_config(config_path: str | Path) -> dict:
    """load alm configuration from json file."""
    path = Path(config_path)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_portfolio_from_config(config: dict) -> CurrentPortfolio:
    """build a currentportfolio entity from config dict."""
    holdings = []
    for h in config.get("portfolio", []):
        holdings.append(PortfolioHolding(
            fund_name=h["fund_name"],
            balance=h["balance"],
            weight=h["weight"],
            benchmark=h["benchmark"],
            regulatory_article=RegulatoryArticle(h["regulatory_article"]),
            segment=AssetSegment(h["segment"]),
            liquidity_days=h["liquidity_days"],
            maturity_date=h.get("maturity_date"),
            admin_fee=h.get("admin_fee", 0.0),
            monthly_return=h.get("monthly_return", 0.0),
            is_legacy=h.get("is_legacy", False),
        ))

    return CurrentPortfolio(
        reference_date=config["reference_date"],
        total_patrimony=config["patrimony"],
        cash_balance=config.get("cash_balance", 0.0),
        holdings=holdings,
    )


def build_indices_from_config(config: dict) -> list[AssetIndex]:
    """build assetindex list from config dict."""
    indices = []
    for idx in config.get("indices", []):
        indices.append(AssetIndex(
            name=idx["name"],
            segment=AssetSegment(idx["segment"]),
            regulatory_article=RegulatoryArticle(idx["regulatory_article"]),
            projected_real_return=idx["projected_real_return"],
            volatility=idx["volatility"],
            projection_model=ProjectionModel(idx["projection_model"]),
        ))
    return indices


# ---------------------------------------------------------------------------
# core calculations
# ---------------------------------------------------------------------------

def calculate_npv(
    cashflows: list[CashFlowYear],
    rate: float,
    patrimony: float = 0.0,
) -> float:
    """
    calculate the net present value of actuarial flows.

    projects patrimony forward using the given real return rate,
    adding net flows each year. returns the terminal patrimony.

    args:
        cashflows: list of annual actuarial flow data
        rate: annual real return rate (decimal, e.g. 0.10 for 10%)
        patrimony: initial patrimony

    returns:
        terminal patrimony (positive = solvent, negative = insolvent)
    """
    p = patrimony
    for cf in cashflows:
        investment_return = p * rate
        net_flow = cf.total_revenues - cf.total_expenditures
        p = p + investment_return + net_flow

    return p


def calculate_required_return(
    cashflows: list[CashFlowYear],
    patrimony: float,
    tol: float = 1e-6,
) -> float:
    """
    calculate the minimum real return rate needed to maintain solvency.

    uses brent's method to find the rate where terminal patrimony = 0.
    this is the "taxa de equilíbrio" from the lema methodology.

    args:
        cashflows: list of annual actuarial flow data
        patrimony: initial patrimony
        tol: tolerance for the root finding

    returns:
        required real return rate (decimal, e.g. 0.1007 for 10.07%)
    """
    def objective(rate: float) -> float:
        return calculate_npv(cashflows, rate, patrimony)

    # search in a reasonable range (0% to 30%)
    try:
        result = brentq(objective, 0.0, 0.30, xtol=tol)
        return result
    except ValueError:
        # if no root in range, return boundary
        if objective(0.30) > 0:
            return 0.30  # even 0% keeps it solvent
        return 0.30  # needs more than 30%


def calculate_npv_deficit_flows(
    cashflows: list[CashFlowYear],
    actuarial_rate: float,
) -> float:
    """
    calculate present value of all future net flows (deficit).

    uses the actuarial discount rate to bring flows to present value.
    this is the "vpl do fluxo sem investimentos" from lema.
    """
    total_pv = 0.0
    for cf in cashflows:
        net_flow = cf.total_revenues - cf.total_expenditures
        total_pv += net_flow * cf.discount_factor

    return total_pv


def project_patrimony(
    cashflows: list[CashFlowYear],
    patrimony: float,
    annual_return: float,
) -> list[dict]:
    """
    project patrimony year by year with a fixed annual return.

    replicates the lema actuarial flow table columns:
    - receitas previdenciárias (I)
    - despesas previdenciárias (II)
    - fluxo sem investimentos (III = I - II)
    - resultado dos investimentos (IV)
    - fluxo anual projetado (V = III + IV)
    - patrimônio projetado

    returns:
        list of dicts with yearly projection data
    """
    projections = []
    p = patrimony

    for cf in cashflows:
        revenues = cf.total_revenues
        expenditures = cf.total_expenditures
        flow_without_inv = revenues - expenditures
        investment_result = p * annual_return
        annual_flow = flow_without_inv + investment_result
        p = p + annual_flow

        projections.append({
            "year": cf.year,
            "revenues": revenues,
            "expenditures": expenditures,
            "flow_without_investments": flow_without_inv,
            "investment_result": investment_result,
            "annual_flow": annual_flow,
            "projected_patrimony": p,
        })

    return projections


# ---------------------------------------------------------------------------
# bond matching
# ---------------------------------------------------------------------------

BOND_PERIODS = [
    ("2028-2029", "NTNB 2028", 2028, 2029),
    ("2030-2034", "NTNB 2030", 2030, 2034),
    ("2035-2039", "NTNB 2035", 2035, 2039),
    ("2040-2044", "NTNB 2040", 2040, 2044),
    ("2045-2049", "NTNB 2045", 2045, 2049),
    ("2050-2054", "NTNB 2050", 2050, 2054),
    ("2055-2059", "NTNB 2055", 2055, 2059),
    ("2060+", "NTNB 2060", 2060, 9999),
]

# indicative rates (to be updated with anbima data)
DEFAULT_NTNB_RATES = {
    "NTNB 2028": 8.02,
    "NTNB 2030": 7.80,
    "NTNB 2035": 7.51,
    "NTNB 2040": 7.28,
    "NTNB 2045": 7.24,
    "NTNB 2050": 7.18,
    "NTNB 2055": 7.18,
    "NTNB 2060": 7.19,
}


def match_bonds_to_liabilities(
    cashflows: list[CashFlowYear],
    actuarial_rate: float,
    bond_allocation_pct: float = 0.30,
    patrimony: float = 0.0,
    ntnb_rates: dict[str, float] | None = None,
) -> list[BondAllocation]:
    """
    liability-driven ntn-b allocation following lema methodology.

    1. group deficit flows by period (5-year buckets)
    2. calculate pv of each bucket at actuarial rate
    3. allocate proportionally to ntn-b matching maturities
    """
    if ntnb_rates is None:
        ntnb_rates = DEFAULT_NTNB_RATES

    rate = actuarial_rate / 100.0

    # group flows by period and calculate pv
    period_pvs: dict[str, float] = {}
    for period_name, bond_name, start_year, end_year in BOND_PERIODS:
        pv = 0.0
        for cf in cashflows:
            if start_year <= cf.year <= end_year:
                net_flow = cf.total_revenues - cf.total_expenditures
                if net_flow < 0:  # only deficit flows
                    years_from_now = cf.year - cashflows[0].year
                    pv += net_flow / ((1 + rate) ** years_from_now)
        period_pvs[period_name] = pv

    total_pv = sum(abs(v) for v in period_pvs.values())
    if total_pv == 0:
        return []

    # calculate allocations
    allocations = []
    for period_name, bond_name, _, _ in BOND_PERIODS:
        pv = period_pvs.get(period_name, 0.0)
        if pv >= 0:  # skip surplus periods
            continue

        weight_portfolio = abs(pv) / total_pv
        weight_total = weight_portfolio * bond_allocation_pct
        bond_rate = ntnb_rates.get(bond_name, 7.0)

        allocations.append(BondAllocation(
            period=period_name,
            pv_flows=pv,
            weight_portfolio=weight_portfolio,
            weight_total=weight_total,
            bond_name=bond_name,
            rate=bond_rate,
        ))

    return allocations


# ---------------------------------------------------------------------------
# solvency simulation (monte carlo)
# ---------------------------------------------------------------------------

def generate_return_scenarios(
    mean_return: float,
    volatility: float,
    n_scenarios: int = 1000,
    n_years: int = 72,
    seed: int = 42,
) -> np.ndarray:
    """
    generate return scenarios using geometric brownian motion.

    R_t = exp((mu - sigma^2/2) + sigma * Z_t) - 1
    where Z_t ~ N(0, 1)

    args:
        mean_return: expected annual real return (decimal)
        volatility: annual standard deviation (decimal)
        n_scenarios: number of monte carlo paths
        n_years: projection horizon
        seed: random seed for reproducibility

    returns:
        ndarray of shape (n_scenarios, n_years) with annual returns
    """
    rng = np.random.default_rng(seed)

    if volatility <= 0:
        # deterministic return (e.g. marcação na curva)
        return np.full((n_scenarios, n_years), mean_return)

    drift = mean_return - (volatility ** 2) / 2
    z = rng.standard_normal((n_scenarios, n_years))
    returns = np.exp(drift + volatility * z) - 1

    return returns


def simulate_solvency(
    cashflows: list[CashFlowYear],
    patrimony: float,
    return_scenarios: np.ndarray,
    inflation_scenarios: np.ndarray,
    actuarial_rate: float,
) -> dict:
    """
    run solvency simulation for a set of return scenarios.

    for each scenario, projects patrimony through the actuarial flow
    and computes funding ratio = At / Lt.

    returns:
        dict with statistics and raw paths
    """
    n_scenarios, n_years = return_scenarios.shape
    actual_years = min(n_years, len(cashflows))
    rate = actuarial_rate / 100.0

    # project patrimony paths
    patrimony_paths = np.zeros((n_scenarios, actual_years))

    for s in range(n_scenarios):
        p = patrimony
        for t in range(actual_years):
            cf = cashflows[t]
            real_return = return_scenarios[s, t]
            inv_result = p * real_return
            net_flow = cf.total_revenues - cf.total_expenditures
            p = p + inv_result + net_flow
            patrimony_paths[s, t] = p

    # compute liability pv at each time step
    liability_pv = np.zeros(actual_years)
    for t in range(actual_years):
        pv = 0.0
        for future_t in range(t, actual_years):
            cf = cashflows[future_t]
            expenditure = cf.total_expenditures
            years_ahead = future_t - t
            pv += expenditure / ((1 + rate) ** years_ahead)
        liability_pv[t] = pv

    # funding ratios
    funding_ratios = np.zeros((n_scenarios, actual_years))
    for t in range(actual_years):
        if liability_pv[t] != 0:
            funding_ratios[:, t] = patrimony_paths[:, t] / liability_pv[t]

    # aggregate statistics
    all_returns = return_scenarios[:, :actual_years].flatten()
    positive_pct = (all_returns > 0).mean() * 100

    median_patrimony = np.median(patrimony_paths, axis=0).tolist()
    median_fr = np.median(funding_ratios, axis=0).tolist()

    return {
        "n_scenarios": n_scenarios,
        "n_years": actual_years,
        "pct_positive_returns": round(positive_pct, 2),
        "min_return": round(float(all_returns.min()) * 100, 2),
        "mean_return": round(float(all_returns.mean()) * 100, 2),
        "max_return": round(float(all_returns.max()) * 100, 2),
        "pct_solvent": round((funding_ratios >= 1).mean() * 100, 2),
        "mean_funding_ratio": round(float(np.median(funding_ratios)), 4),
        "quantile_5_funding_ratio": round(float(np.quantile(funding_ratios, 0.05)), 4),
        "yearly_median_patrimony": median_patrimony,
        "yearly_median_funding_ratio": median_fr,
    }


# ---------------------------------------------------------------------------
# main orchestrator
# ---------------------------------------------------------------------------

class ALMEngine:
    """main alm engine that orchestrates the full study."""

    def __init__(self, config_path: str | Path):
        self.config = load_alm_config(config_path)
        self.portfolio = build_portfolio_from_config(self.config)
        self.indices = build_indices_from_config(self.config)
        self.cashflows: list[CashFlowYear] = []
        self.metadata: dict = {}

    def load_cashflows(self, csv_path: str | Path | None = None) -> None:
        """load actuarial flow from cadprev csv."""
        if csv_path is None:
            csv_path = self.config.get("cashflow_csv_path", "")
        self.cashflows, self.metadata = parse_cadprev_csv(csv_path)

    def run(self, n_scenarios: int = 1000, horizon_years: int = 30) -> ALMResult:
        """
        run the complete alm study.

        returns an almresult with all computed data.
        """
        if not self.cashflows:
            self.load_cashflows()

        patrimony = self.config["patrimony"]
        actuarial_rate = self.config["actuarial_rate"]

        # step 1: required return
        required_return = calculate_required_return(
            self.cashflows, patrimony
        )

        # step 2: npv of deficit flows
        npv_deficit = calculate_npv_deficit_flows(
            self.cashflows, actuarial_rate
        )

        # step 3: bond matching
        bond_allocations = match_bonds_to_liabilities(
            self.cashflows,
            actuarial_rate,
            bond_allocation_pct=0.30,
            patrimony=patrimony,
        )

        # step 4: markowitz optimization (10 portfolios on efficient frontier)
        from app.application.services.alm_markowitz import (
            build_efficient_frontier, recommend_portfolio,
        )

        # identify locked (illiquid) positions — vértice funds
        locked_positions: dict[str, float] = {}
        total_inv = self.portfolio.total_invested
        index_map = {idx.name: idx for idx in self.indices}

        for h in self.portfolio.holdings:
            if h.maturity_date is not None:  # vértice fund
                w = h.balance / total_inv if total_inv > 0 else 0
                # map to the closest index
                if h.benchmark in index_map:
                    locked_positions[h.benchmark] = (
                        locked_positions.get(h.benchmark, 0) + w
                    )

        pro_gestao = self.config.get("pro_gestao_level")

        efficient_frontier = build_efficient_frontier(
            self.indices,
            n_portfolios=10,
            pro_gestao_level=pro_gestao,
            locked_positions=locked_positions,
            risk_free_rate=0.0,
        )

        recommended = recommend_portfolio(efficient_frontier)

        # step 5: solvency simulation for recommended portfolio
        benchmark_weights = self.portfolio.benchmark_breakdown
        avg_return = 0.0
        avg_vol = 0.0

        if recommended:
            # use recommended portfolio weights for simulation
            for idx_name, w in recommended.weights.items():
                if idx_name in index_map:
                    idx = index_map[idx_name]
                    avg_return += w * idx.projected_real_return / 100
                    avg_vol += w * idx.volatility / 100
        else:
            # fallback to current portfolio weights
            for bench, balance in benchmark_weights.items():
                w = balance / total_inv if total_inv > 0 else 0
                if bench in index_map:
                    idx = index_map[bench]
                    avg_return += w * idx.projected_real_return / 100
                    avg_vol += w * idx.volatility / 100

        limited_cashflows = self.cashflows[:horizon_years]
        return_scenarios = generate_return_scenarios(
            avg_return, avg_vol,
            n_scenarios=n_scenarios,
            n_years=horizon_years,
        )
        inflation_scenarios = generate_return_scenarios(
            self.config.get("inflation_implicit_2268", 5.74) / 100,
            0.03,
            n_scenarios=n_scenarios,
            n_years=horizon_years,
            seed=123,
        )

        solvency = simulate_solvency(
            limited_cashflows, patrimony,
            return_scenarios, inflation_scenarios,
            actuarial_rate,
        )

        solvency_result = SolvencyResult(
            portfolio_id=recommended.portfolio_id if recommended else 0,
            n_scenarios=solvency["n_scenarios"],
            n_years=solvency["n_years"],
            pct_positive_returns=solvency["pct_positive_returns"],
            min_return=solvency["min_return"],
            mean_return=solvency["mean_return"],
            max_return=solvency["max_return"],
            pct_solvent=solvency["pct_solvent"],
            mean_funding_ratio=solvency["mean_funding_ratio"],
            quantile_5_funding_ratio=solvency["quantile_5_funding_ratio"],
            yearly_median_patrimony=solvency["yearly_median_patrimony"],
            yearly_median_funding_ratio=solvency["yearly_median_funding_ratio"],
        )

        # step 6: gap analysis (current vs recommended)
        gap_table: dict[str, dict[str, float]] = {}
        for bench, balance in benchmark_weights.items():
            current_pct = (balance / total_inv * 100) if total_inv > 0 else 0
            recommended_pct = 0.0
            if recommended:
                recommended_pct = recommended.weight_for(bench) * 100
            gap_table[bench] = {
                "current_pct": round(current_pct, 2),
                "current_value": balance,
                "recommended_pct": round(recommended_pct, 2),
                "gap_pct": round(recommended_pct - current_pct, 2),
            }

        return ALMResult(
            rpps_name=self.config["rpps_name"],
            reference_date=self.config["reference_date"],
            actuarial_rate=actuarial_rate,
            current_portfolio=self.portfolio,
            cashflows=self.cashflows,
            indices=self.indices,
            patrimony=patrimony,
            required_return=round(required_return * 100, 2),
            npv_deficit_flows=round(npv_deficit, 2),
            meta_atuarial=actuarial_rate,
            efficient_frontier=efficient_frontier,
            recommended_portfolio=recommended,
            solvency_results=[solvency_result],
            bond_allocations=bond_allocations,
            gap_table=gap_table,
        )
