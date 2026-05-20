"""
risk metrics engine — institutional-grade indicators.
mirrors the metrics used by rpps investment committees:
var, sharpe, treynor, drawdown, volatility, tracking error.
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class RiskReport:
    """all risk metrics for a single fund or the whole portfolio."""
    # performance
    return_month: float
    return_12m: float
    # risk
    var_month: float          # value at risk (parametric, 95%, 252 d.u.)
    var_12m: float
    volatility_month: float   # annualized std dev of returns
    volatility_12m: float
    # risk-adjusted
    sharpe_month: float       # (ret - rf) / vol
    sharpe_12m: float
    treynor_month: float      # (ret - rf) / beta
    treynor_12m: float
    # downside
    drawdown_month: float     # max drawdown in the period
    drawdown_12m: float
    # benchmark comparison
    benchmark: str
    alpha: float              # excess return vs benchmark
    beta: float               # sensitivity to benchmark
    tracking_error: float     # std of (fund_ret - bench_ret)
    information_ratio: float  # alpha / tracking_error


class RiskMetricsEngine:
    """
    calculates institutional risk metrics from return series.
    replicates the exact metrics found in rpps/ipsemb risk reports:
    var, vol, sharpe, treynor, drawdown — monthly and 12-month windows.
    """

    def __init__(self, risk_free_rate_monthly: float = 0.009):
        """
        args:
            risk_free_rate_monthly: monthly risk-free rate (default ~1% = cdi)
        """
        self.rf_monthly = risk_free_rate_monthly
        self.rf_annual = (1 + risk_free_rate_monthly) ** 12 - 1

    def compute(
        self,
        returns: np.ndarray,
        benchmark_returns: Optional[np.ndarray] = None,
        benchmark_name: str = "CDI",
        confidence: float = 0.95,
    ) -> RiskReport:
        """
        compute the full risk report for a return series.

        args:
            returns: array of monthly returns (e.g. 0.01 = 1%)
            benchmark_returns: array of benchmark monthly returns (same length)
            benchmark_name: name string for display
            confidence: var confidence level (0.95 = 95%)
        """
        if len(returns) < 2:
            return self._empty_report(benchmark_name)

        # split into recent month and trailing 12m
        ret_month = returns[-1] if len(returns) >= 1 else 0.0
        ret_12m_arr = returns[-12:] if len(returns) >= 12 else returns
        ret_12m = float(np.prod(1 + ret_12m_arr) - 1)

        # volatility (annualized)
        vol_month = float(np.std(returns[-21:]) if len(returns) >= 21 else np.std(returns))
        vol_12m = float(np.std(ret_12m_arr) * np.sqrt(12))

        # var — parametric normal (95%, 252 d.u. scaled to monthly)
        var_month = float(self._parametric_var(returns[-21:], confidence)) if len(returns) >= 21 else 0.0
        var_12m = float(self._parametric_var(ret_12m_arr, confidence))

        # sharpe
        sharpe_month = self._sharpe(ret_month, vol_month)
        sharpe_12m = self._sharpe(ret_12m / max(len(ret_12m_arr), 1), vol_12m / np.sqrt(12)) if vol_12m > 0 else 0.0

        # beta, alpha, tracking error, information ratio
        if benchmark_returns is not None and len(benchmark_returns) >= 2:
            min_len = min(len(returns), len(benchmark_returns))
            r = returns[-min_len:]
            b = benchmark_returns[-min_len:]

            beta = float(self._beta(r, b))
            alpha = float(np.mean(r) - self.rf_monthly - beta * (np.mean(b) - self.rf_monthly))
            te = float(np.std(r - b))
            ir = float(alpha / te) if te > 1e-10 else 0.0
        else:
            beta = 1.0
            alpha = 0.0
            te = 0.0
            ir = 0.0

        # treynor
        treynor_month = float((ret_month - self.rf_monthly) / beta) if abs(beta) > 1e-10 else 0.0
        treynor_12m = float((ret_12m - self.rf_annual) / beta) if abs(beta) > 1e-10 else 0.0

        # drawdown
        dd_month = float(self._max_drawdown(returns[-21:])) if len(returns) >= 21 else 0.0
        dd_12m = float(self._max_drawdown(ret_12m_arr))

        return RiskReport(
            return_month=float(ret_month),
            return_12m=float(ret_12m),
            var_month=var_month,
            var_12m=var_12m,
            volatility_month=vol_month,
            volatility_12m=vol_12m,
            sharpe_month=sharpe_month,
            sharpe_12m=sharpe_12m,
            treynor_month=treynor_month,
            treynor_12m=treynor_12m,
            drawdown_month=dd_month,
            drawdown_12m=dd_12m,
            benchmark=benchmark_name,
            alpha=alpha,
            beta=beta,
            tracking_error=te,
            information_ratio=ir,
        )

    def compute_portfolio(
        self,
        asset_returns: Dict[str, np.ndarray],
        weights: Dict[str, float],
        benchmark_returns: Optional[np.ndarray] = None,
        benchmark_name: str = "Meta Atuarial",
    ) -> RiskReport:
        """
        compute risk metrics for a weighted portfolio.

        args:
            asset_returns: dict of asset_name -> monthly return arrays
            weights: dict of asset_name -> weight (0 to 1)
            benchmark_returns: benchmark return array
            benchmark_name: benchmark label
        """
        # align lengths
        min_len = min(len(r) for r in asset_returns.values()) if asset_returns else 0
        if min_len < 2:
            return self._empty_report(benchmark_name)

        portfolio_returns = np.zeros(min_len)
        for name, rets in asset_returns.items():
            w = weights.get(name, 0.0)
            portfolio_returns += w * rets[-min_len:]

        bench = benchmark_returns[-min_len:] if benchmark_returns is not None else None
        return self.compute(portfolio_returns, bench, benchmark_name)

    # ── private helpers ──

    def _parametric_var(self, returns: np.ndarray, confidence: float = 0.95) -> float:
        """parametric var assuming normal distribution."""
        from scipy.stats import norm
        z = norm.ppf(1 - confidence)
        mu = np.mean(returns)
        sigma = np.std(returns)
        return float(abs(mu + z * sigma))

    def _sharpe(self, excess_return: float, volatility: float) -> float:
        if abs(volatility) < 1e-10:
            return 0.0
        return float((excess_return - self.rf_monthly) / volatility)

    def _beta(self, returns: np.ndarray, benchmark: np.ndarray) -> float:
        if len(returns) < 2 or np.std(benchmark) < 1e-10:
            return 1.0
        cov = np.cov(returns, benchmark)
        return float(cov[0, 1] / cov[1, 1])

    def _max_drawdown(self, returns: np.ndarray) -> float:
        if len(returns) < 1:
            return 0.0
        cumulative = np.cumprod(1 + returns)
        peak = np.maximum.accumulate(cumulative)
        drawdowns = np.where(peak > 0, (peak - cumulative) / peak, 0)
        return float(np.max(drawdowns))

    def _empty_report(self, benchmark: str) -> RiskReport:
        return RiskReport(
            return_month=0.0, return_12m=0.0,
            var_month=0.0, var_12m=0.0,
            volatility_month=0.0, volatility_12m=0.0,
            sharpe_month=0.0, sharpe_12m=0.0,
            treynor_month=0.0, treynor_12m=0.0,
            drawdown_month=0.0, drawdown_12m=0.0,
            benchmark=benchmark,
            alpha=0.0, beta=1.0,
            tracking_error=0.0, information_ratio=0.0,
        )
