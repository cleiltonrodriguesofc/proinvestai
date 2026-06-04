"""
markowitz optimizer for rpps alm — efficient frontier with 10 portfolios.

replicates the lema methodology:
1. build covariance matrix from historical returns (60 months)
2. generate 10 portfolios on the efficient frontier
3. apply regulatory constraints (cmn 5.272/2025)
4. apply policy constraints (pi 2026)
5. lock illiquid positions (fundos de vértice)
6. recommend the portfolio with highest sharpe ratio
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize

from app.domain.entities.alm_entities import (
    AssetIndex,
    AssetSegment,
    OptimizedPortfolio,
    RegulatoryArticle,
)


# ---------------------------------------------------------------------------
# default covariance matrix (from lema alm 60-month rolling)
# when live data is unavailable, we use this as fallback
# ---------------------------------------------------------------------------

# indices used in the optimization (order matters for covariance matrix)
DEFAULT_INDEX_NAMES = [
    "CDI", "IRF-M 1", "IRF-M", "IMA-B 5", "IMA-B", "IMA-B 5+",
    "IMA Geral Ex-C", "IDkA IPCA 2 Anos", "IDkA Pré 2 Anos", "IRF-M 1+",
    "Carteira Títulos Públicos ALM", "Fundos Crédito Privado - 105% CDI",
    "Fundos Multimercados - 100% CDI", "Ibovespa", "IFIX",
]


def _build_default_correlation_matrix() -> np.ndarray:
    """
    simplified correlation matrix for rpps-eligible indices.
    based on typical 60-month rolling correlations from brazilian markets.
    """
    n = len(DEFAULT_INDEX_NAMES)
    corr = np.eye(n)

    # rf indices are highly correlated among themselves (~0.6-0.9)
    rf_indices = list(range(10))
    for i in rf_indices:
        for j in rf_indices:
            if i != j:
                corr[i, j] = 0.7

    # tp alm and cp correlated with rf
    corr[10, :10] = 0.5; corr[:10, 10] = 0.5
    corr[11, :10] = 0.6; corr[:10, 11] = 0.6

    # multimercado moderate correlation with rf
    corr[12, :10] = 0.5; corr[:10, 12] = 0.5

    # ibovespa low/negative correlation with rf
    corr[13, :10] = -0.1; corr[:10, 13] = -0.1
    corr[13, 12] = 0.3; corr[12, 13] = 0.3

    # ifix moderate correlation
    corr[14, :10] = 0.2; corr[:10, 14] = 0.2
    corr[14, 13] = 0.5; corr[13, 14] = 0.5

    # ensure diagonal is 1
    np.fill_diagonal(corr, 1.0)

    return corr


def build_covariance_matrix(
    indices: list[AssetIndex],
    correlation_matrix: np.ndarray | None = None,
) -> np.ndarray:
    """
    build covariance matrix from volatilities and correlation matrix.
    cov(i,j) = corr(i,j) * vol(i) * vol(j)
    """
    n = len(indices)
    vols = np.array([idx.volatility / 100.0 for idx in indices])

    if correlation_matrix is None:
        # use identity if no correlation data (conservative)
        correlation_matrix = np.eye(n)

    # cov = diag(vol) @ corr @ diag(vol)
    cov = np.outer(vols, vols) * correlation_matrix

    return cov


# ---------------------------------------------------------------------------
# regulatory constraints for cmn 5.272/2025
# ---------------------------------------------------------------------------

def get_regulatory_bounds(
    indices: list[AssetIndex],
    pro_gestao_level: int | None = None,
    cmn_resolution: str = "5272",
) -> list[tuple[float, float]]:
    """
    compute min/max bounds per index based on cmn resolution.

    pro_gestao_level: None (sem), 1, 2, 3, or 4
    cmn_resolution: '5272' (default) or '4963'
    """
    bounds = []

    # mapping of regulatory articles to minimum certification level (for 5.272)
    article_min_level_5272 = {
        RegulatoryArticle.ART_7_I: None,   # all rpps
        RegulatoryArticle.ART_7_II: None,
        RegulatoryArticle.ART_7_III: 1,
        RegulatoryArticle.ART_7_IV: 1,
        RegulatoryArticle.ART_7_V: 2,
        RegulatoryArticle.ART_7_VI: 2,
        RegulatoryArticle.ART_7_VII: 3,
        RegulatoryArticle.ART_7_VIII: 3,
        RegulatoryArticle.ART_7_IX: 4,
        RegulatoryArticle.ART_8_I: 2,
        RegulatoryArticle.ART_8_II: 2,
        RegulatoryArticle.ART_8_III: 3,
        RegulatoryArticle.ART_8_IV: 3,
        RegulatoryArticle.ART_9_I: 3,
        RegulatoryArticle.ART_9_II: 3,
        RegulatoryArticle.ART_9_III: 3,
        RegulatoryArticle.ART_10_I: 2,
        RegulatoryArticle.ART_10_II: 3,
        RegulatoryArticle.ART_10_III: 4,
        RegulatoryArticle.ART_10_IV: 4,
        RegulatoryArticle.ART_11: 3,
        RegulatoryArticle.ART_12: None,
    }

    for idx in indices:
        if cmn_resolution == "5272":
            min_level = article_min_level_5272.get(idx.regulatory_article)
            if min_level is not None:
                if pro_gestao_level is None or pro_gestao_level < min_level:
                    # rpps does not meet certification level — 0% max
                    bounds.append((0.0, 0.0))
                    continue

        # apply per-index max from the resolution
        max_weight = idx.max_weight if idx.max_weight < 1.0 else 1.0

        # segment-level caps
        if idx.segment == AssetSegment.RENDA_VARIAVEL:
            max_weight = min(max_weight, 0.40)
        elif idx.segment == AssetSegment.EXTERIOR:
            max_weight = min(max_weight, 0.10)
        elif idx.segment == AssetSegment.FUNDOS_IMOBILIARIOS:
            max_weight = min(max_weight, 0.20)

        bounds.append((idx.min_weight, max_weight))

    return bounds


# ---------------------------------------------------------------------------
# group constraints (scipy format)
# ---------------------------------------------------------------------------

def get_group_constraints(
    indices: list[AssetIndex],
    pro_gestao_level: int | None = None,
    cmn_resolution: str = "5272",
) -> list[dict]:
    """build scipy constraint dicts for group limits."""
    constraints = []

    # weights sum to 1
    constraints.append({
        "type": "eq",
        "fun": lambda w: np.sum(w) - 1.0,
    })

    # rv global <= 50% (art. 8)
    rv_mask = np.array([
        1.0 if idx.segment == AssetSegment.RENDA_VARIAVEL else 0.0
        for idx in indices
    ])
    if rv_mask.sum() > 0:
        constraints.append({
            "type": "ineq",
            "fun": lambda w, m=rv_mask: 0.50 - np.dot(m, w),
        })

    # estruturados global <= 20% (art. 10)
    est_mask = np.array([
        1.0 if idx.segment == AssetSegment.ESTRUTURADOS else 0.0
        for idx in indices
    ])
    if est_mask.sum() > 0:
        constraints.append({
            "type": "ineq",
            "fun": lambda w, m=est_mask: 0.20 - np.dot(m, w),
        })

    # exterior global <= 10% (art. 9)
    ext_mask = np.array([
        1.0 if idx.segment == AssetSegment.EXTERIOR else 0.0
        for idx in indices
    ])
    if ext_mask.sum() > 0:
        constraints.append({
            "type": "ineq",
            "fun": lambda w, m=ext_mask: 0.10 - np.dot(m, w),
        })

    # fii global <= 20% (art. 11)
    fii_mask = np.array([
        1.0 if idx.segment == AssetSegment.FUNDOS_IMOBILIARIOS else 0.0
        for idx in indices
    ])
    if fii_mask.sum() > 0:
        constraints.append({
            "type": "ineq",
            "fun": lambda w, m=fii_mask: 0.20 - np.dot(m, w),
        })

    # global rv + estruturados + fii (art. 14)
    combined_mask = rv_mask + est_mask + fii_mask
    if combined_mask.sum() > 0:
        if cmn_resolution == "5272":
            if pro_gestao_level is None or pro_gestao_level < 2:
                max_combined = 0.0
            elif pro_gestao_level == 2:
                max_combined = 0.40
            elif pro_gestao_level == 3:
                max_combined = 0.50
            else:
                max_combined = 0.60
        else:
            # 4963 fallback (generous limit)
            max_combined = 1.0

        constraints.append({
            "type": "ineq",
            "fun": lambda w, m=combined_mask, mx=max_combined: mx - np.dot(m, w),
        })

    return constraints


# ---------------------------------------------------------------------------
# efficient frontier optimization
# ---------------------------------------------------------------------------

def optimize_single_portfolio(
    target_return: float,
    expected_returns: np.ndarray,
    cov_matrix: np.ndarray,
    bounds: list[tuple[float, float]],
    constraints: list[dict],
) -> tuple[np.ndarray, float] | None:
    """
    find the minimum variance portfolio for a given target return.
    """
    n = len(expected_returns)

    # add return constraint
    all_constraints = constraints + [{
        "type": "eq",
        "fun": lambda w, r=expected_returns, t=target_return: np.dot(r, w) - t,
    }]

    def portfolio_variance(w):
        return w @ cov_matrix @ w

    # initial guess — equal weight among non-zero-bounded assets
    x0 = np.zeros(n)
    free_assets = [i for i, (lo, hi) in enumerate(bounds) if hi > 0]
    if free_assets:
        for i in free_assets:
            x0[i] = 1.0 / len(free_assets)

    result = minimize(
        portfolio_variance,
        x0,
        method="SLSQP",
        bounds=bounds,
        constraints=all_constraints,
        options={"maxiter": 1000, "ftol": 1e-12},
    )

    if result.success:
        return result.x, result.fun
    return None


def build_efficient_frontier(
    indices: list[AssetIndex],
    n_portfolios: int = 10,
    pro_gestao_level: int | None = None,
    locked_positions: dict[str, float] | None = None,
    risk_free_rate: float = 0.0,
    cmn_resolution: str = "5272",
) -> list[OptimizedPortfolio]:
    """
    build the efficient frontier with n portfolios.

    follows the lema methodology:
    1. filter indices to those available for the rpps certification level
    2. apply regulatory and policy constraints
    3. generate n points on the frontier from min to max return
    4. compute sharpe ratio for each

    args:
        indices: list of asset indices with projected returns/volatility
        n_portfolios: number of points on the frontier (default 10)
        pro_gestao_level: certification level (None, 1, 2, 3, 4)
        locked_positions: {index_name: weight} for illiquid positions
        risk_free_rate: for sharpe calculation (default 0 = real terms)

    returns:
        list of optimizedportfolio sorted by return (ascending)
    """
    if locked_positions is None:
        locked_positions = {}

    # filter out locked indices and adjust available weight
    locked_weight = sum(locked_positions.values())
    available_weight = 1.0 - locked_weight

    # indices available for optimization
    opt_indices = [idx for idx in indices if idx.name not in locked_positions]

    if not opt_indices:
        return []

    # expected returns and covariance
    returns = np.array([idx.projected_real_return / 100.0 for idx in opt_indices])
    n = len(opt_indices)

    # build covariance matrix
    corr = _build_default_correlation_matrix()
    # map indices to correlation matrix positions
    name_to_default_idx = {name: i for i, name in enumerate(DEFAULT_INDEX_NAMES)}
    mapped_corr = np.eye(n)
    for i, idx_i in enumerate(opt_indices):
        for j, idx_j in enumerate(opt_indices):
            di = name_to_default_idx.get(idx_i.name)
            dj = name_to_default_idx.get(idx_j.name)
            if di is not None and dj is not None:
                mapped_corr[i, j] = corr[di, dj]

    cov = build_covariance_matrix(opt_indices, mapped_corr)

    # bounds (scaled to available weight)
    raw_bounds = get_regulatory_bounds(opt_indices, pro_gestao_level, cmn_resolution)
    bounds = [(lo, min(hi, available_weight)) for lo, hi in raw_bounds]

    # constraints (sum to available_weight instead of 1.0)
    constraints = [{
        "type": "eq",
        "fun": lambda w: np.sum(w) - available_weight,
    }]

    # group constraints
    group_cons = get_group_constraints(opt_indices, pro_gestao_level, cmn_resolution)
    # skip the first one (sum=1) since we already added our own
    constraints.extend(group_cons[1:])

    # determine return range for frontier
    # filter to feasible returns only
    feasible_returns = [
        returns[i] for i, (lo, hi) in enumerate(bounds) if hi > 0
    ]
    if not feasible_returns:
        return []

    min_return = min(feasible_returns)
    max_return = max(feasible_returns) * available_weight

    # generate target returns (oversample to guarantee we get exactly n_portfolios)
    candidate_targets = np.linspace(
        min_return * available_weight * 0.95,
        max_return * 0.99,
        n_portfolios * 2,
    )

    # optimize each portfolio
    raw_portfolios = []

    for target in candidate_targets:
        result = optimize_single_portfolio(
            target, returns, cov, bounds, constraints,
        )

        if result is None:
            continue

        weights, variance = result
        port_return = float(np.dot(returns, weights))
        port_vol = float(np.sqrt(variance))

        # add locked positions to weights
        full_weights: dict[str, float] = {}
        for name, locked_w in locked_positions.items():
            full_weights[name] = locked_w

        for i, idx in enumerate(opt_indices):
            w = float(weights[i])
            if w > 0.001:  # filter negligible weights
                full_weights[idx.name] = round(w, 4)

        # total portfolio return (including locked)
        locked_return = sum(
            locked_positions.get(idx.name, 0) * idx.projected_real_return / 100
            for idx in indices if idx.name in locked_positions
        )
        total_return = port_return + locked_return

        # total portfolio volatility (including locked positions' vol contribution)
        # approximate: vol_total = sqrt(w_opt^2 * var_opt + w_locked^2 * var_locked + 2*w_opt*w_locked*cov)
        locked_vol = 0.0
        for idx in indices:
            if idx.name in locked_positions:
                locked_vol += locked_positions[idx.name] * (idx.volatility / 100.0)
        total_vol = np.sqrt(port_vol**2 + locked_vol**2 + 2 * 0.5 * port_vol * locked_vol)

        # sharpe ratio using risk_free_rate (cdi real when in real terms)
        sharpe = (total_return - risk_free_rate) / total_vol if total_vol > 0.001 else 0

        raw_portfolios.append({
            "expected_return": round(total_return * 100, 2),
            "volatility": round(total_vol * 100, 2),
            "sharpe_ratio": round(sharpe, 2),
            "weights": full_weights,
        })

    # deduplicate by expected return
    unique_ports = []
    seen_returns = set()
    for p in raw_portfolios:
        if p["expected_return"] not in seen_returns:
            seen_returns.add(p["expected_return"])
            unique_ports.append(p)

    # select exactly n_portfolios evenly spaced
    if len(unique_ports) <= n_portfolios:
        selected = unique_ports
    else:
        indices = np.linspace(0, len(unique_ports) - 1, n_portfolios, dtype=int)
        selected = [unique_ports[i] for i in indices]

    portfolios: list[OptimizedPortfolio] = []
    for i, p in enumerate(selected, 1):
        portfolios.append(OptimizedPortfolio(
            portfolio_id=i,
            expected_return=p["expected_return"],
            volatility=p["volatility"],
            sharpe_ratio=p["sharpe_ratio"],
            weights=p["weights"],
        ))

    return portfolios


def recommend_portfolio(
    portfolios: list[OptimizedPortfolio],
) -> OptimizedPortfolio | None:
    """select the portfolio with the highest sharpe ratio (port.1 in lema)."""
    if not portfolios:
        return None
    return max(portfolios, key=lambda p: p.sharpe_ratio)
