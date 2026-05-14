"""
market data service — aggregates benchmark data from multiple sources.
bcb sgs: cdi, selic, ipca, igpm
anbima: irfm, ima-b, ima-geral (via bcb proxy series)
b3/yahoo: ibovespa, smll, idiv, ifix
"""

import logging
from datetime import datetime
from typing import Dict, Optional
import numpy as np
from .bcb_api import BCBApiClient

logger = logging.getLogger(__name__)

# bcb sgs series codes for all supported benchmarks
BENCHMARK_SERIES = {
    # renda fixa — bcb sgs
    "CDI": 4391,           # cdi daily accumulated
    "SELIC": 11,           # selic efetiva daily
    "IPCA": 433,           # ipca monthly
    "IGPM": 25433,         # igp-m monthly
    "POUPANCA": 25,        # poupanca monthly
    # renda fixa — anbima indices via bcb sgs proxy
    "IRF-M": 12462,        # irf-m total return
    "IRF-M 1": 12461,      # irf-m 1 year (pre-fixado curto)
    "IMA-B": 12466,        # ima-b total return (ipca linked)
    "IMA-B 5": 12467,      # ima-b 5 (ipca linked short)
    "IMA-B 5+": 12468,     # ima-b 5+ (ipca linked long)
    "IMA Geral": 12460,    # ima geral total return
    "IMA Geral ex-C": 28547,  # ima geral ex-c
}

# b3 equity indices — fetched via yahoo finance ticker
EQUITY_TICKERS = {
    "IBOVESPA": "^BVSP",
    "IBrX-100": "^IBX100",
    "SMLL": "SMAL11.SA",
    "IDIV": "DIVO11.SA",
    "IFIX": "IFIX.SA",
    "IHFA": None,           # no public proxy available
}


class MarketDataService:
    """
    unified service to fetch historical returns for all benchmarks.
    uses bcb sgs for fixed-income and anbima indices,
    and yahoo finance for equity indices.
    """

    def __init__(self, bcb_client: Optional[BCBApiClient] = None):
        self.bcb = bcb_client or BCBApiClient()
        self._cache: Dict[str, np.ndarray] = {}

    def get_benchmark_returns(
        self, benchmark: str, start_year: int = 2015
    ) -> np.ndarray:
        """
        get monthly return series for a benchmark.
        returns numpy array of monthly returns.
        """
        cache_key = f"{benchmark}_{start_year}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        returns = np.array([])

        if benchmark in BENCHMARK_SERIES:
            returns = self._fetch_bcb_series(benchmark, start_year)
        elif benchmark in EQUITY_TICKERS and EQUITY_TICKERS[benchmark]:
            returns = self._fetch_equity_series(benchmark, start_year)
        else:
            logger.warning(f"no data source for benchmark: {benchmark}")
            return returns

        if len(returns) > 0:
            self._cache[cache_key] = returns

        return returns

    def get_all_benchmarks(
        self, benchmarks: list[str], start_year: int = 2015
    ) -> Dict[str, np.ndarray]:
        """fetch returns for multiple benchmarks at once."""
        result = {}
        for bench in benchmarks:
            rets = self.get_benchmark_returns(bench, start_year)
            if len(rets) > 0:
                result[bench] = rets
        return result

    def get_risk_free_rate(self) -> float:
        """get current monthly risk-free rate (cdi)."""
        try:
            cdi = self.bcb.get_cdi_current()
            # convert annual to monthly
            return (1 + cdi / 100) ** (1 / 12) - 1
        except Exception:
            return 0.009  # fallback ~1% monthly

    # ── private fetchers ──

    def _fetch_bcb_series(self, benchmark: str, start_year: int) -> np.ndarray:
        """fetch from bcb sgs and convert to monthly returns."""
        series_id = BENCHMARK_SERIES[benchmark]
        start_date = f"01/01/{start_year}"
        end_date = datetime.now().strftime("%d/%m/%Y")
        url = (
            f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{series_id}"
            f"/dados?formato=json&dataInicial={start_date}&dataFinal={end_date}"
        )

        try:
            data = self.bcb._http_get_json(url)
            if not data:
                return np.array([])

            # daily series (cdi, selic, irfm, ima) → accumulate to monthly
            if benchmark in ("CDI", "SELIC", "IRF-M", "IRF-M 1",
                             "IMA-B", "IMA-B 5", "IMA-B 5+",
                             "IMA Geral", "IMA Geral ex-C"):
                return self._daily_to_monthly_returns(data)
            else:
                # monthly series (ipca, igpm, poupanca) — already monthly
                return self._parse_monthly_series(data)

        except Exception as e:
            logger.error(f"failed to fetch {benchmark} (series {series_id}): {e}")
            return np.array([])

    def _fetch_equity_series(self, benchmark: str, start_year: int) -> np.ndarray:
        """fetch equity index via yahoo finance."""
        ticker = EQUITY_TICKERS.get(benchmark)
        if not ticker:
            return np.array([])

        try:
            import yfinance as yf
            start = f"{start_year}-01-01"
            df = yf.download(ticker, start=start, interval="1mo", progress=False)
            if df.empty:
                return np.array([])

            # calculate monthly returns from adjusted close
            prices = df["Adj Close"].values.flatten()
            returns = np.diff(prices) / prices[:-1]
            return returns

        except ImportError:
            logger.warning("yfinance not installed — equity data unavailable")
            return np.array([])
        except Exception as e:
            logger.error(f"failed to fetch {benchmark} ({ticker}): {e}")
            return np.array([])

    def _daily_to_monthly_returns(self, daily_data: list) -> np.ndarray:
        """accumulate daily factor data into monthly returns."""
        monthly_factors = {}
        for d in daily_data:
            try:
                dt = datetime.strptime(d["data"], "%d/%m/%Y")
                key = dt.strftime("%Y-%m")
                daily_rate = float(d["valor"]) / 100
                if key not in monthly_factors:
                    monthly_factors[key] = 1.0
                monthly_factors[key] *= (1 + daily_rate)
            except (ValueError, KeyError):
                continue

        # sort by date and convert to returns
        sorted_months = sorted(monthly_factors.keys())
        return np.array([monthly_factors[m] - 1 for m in sorted_months])

    def _parse_monthly_series(self, data: list) -> np.ndarray:
        """parse monthly percentage data (ipca, igpm)."""
        monthly = {}
        for d in data:
            try:
                dt = datetime.strptime(d["data"], "%d/%m/%Y")
                key = dt.strftime("%Y-%m")
                monthly[key] = float(d["valor"]) / 100
            except (ValueError, KeyError):
                continue

        sorted_months = sorted(monthly.keys())
        return np.array([monthly[m] for m in sorted_months])
