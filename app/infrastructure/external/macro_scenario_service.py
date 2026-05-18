"""
macro scenario service — builds forward-looking economic scenarios
from real-time bcb data and focus market expectations.

uses lazy initialization and caching to avoid hammering bcb apis.
falls back to consensus values if apis are unavailable.
"""

import logging
import numpy as np
from typing import Dict, Optional
from datetime import datetime
from .bcb_api import BCBApiClient

logger = logging.getLogger(__name__)

# consensus values (may 2026 focus median — updated manually)
_FALLBACK = {
    "selic_current": 14.75,
    "ipca_12m": 5.53,
    "cdi_annual": 14.65,
    "focus_selic": {2026: 14.75, 2027: 12.50, 2028: 10.50, 2029: 10.00, 2030: 10.00},
    "focus_ipca": {2026: 5.53, 2027: 4.50, 2028: 4.00, 2029: 3.75, 2030: 3.50},
}


class MacroScenario:
    """
    immutable snapshot of the current macro environment.
    provides forward-looking paths for selic, cdi, and ipca
    via linear interpolation of focus annual projections.
    """

    def __init__(
        self,
        selic_current: float,
        ipca_12m: float,
        cdi_annual: float,
        focus_selic: Dict[int, float],
        focus_ipca: Dict[int, float],
    ):
        self.selic_current = selic_current
        self.ipca_12m = ipca_12m
        self.cdi_annual = cdi_annual
        self.focus_selic = focus_selic
        self.focus_ipca = focus_ipca

    def build_selic_path(self, horizon_months: int) -> np.ndarray:
        return self._interpolate_annual_to_monthly(
            self.selic_current / 100, self.focus_selic, horizon_months
        )

    def build_ipca_path(self, horizon_months: int) -> np.ndarray:
        return self._interpolate_annual_to_monthly(
            self.ipca_12m / 100, self.focus_ipca, horizon_months
        )

    def build_cdi_path(self, horizon_months: int) -> np.ndarray:
        # cdi tracks selic with ~0.10pp spread below
        return np.maximum(self.build_selic_path(horizon_months) - 0.001, 0.0)

    def get_expected_return(self, benchmark: str) -> float:
        """
        estimate forward-looking 12m expected return for a benchmark,
        using the interpolated macro paths from focus projections.
        """
        cdi_path = self.build_cdi_path(12)
        ipca_path = self.build_ipca_path(12)

        avg_cdi = float(np.mean(cdi_path))
        avg_ipca = float(np.mean(ipca_path))

        if "CDI" in benchmark or "SELIC" in benchmark:
            return avg_cdi
        if "IRF-M" in benchmark:
            return avg_cdi * 1.02  # short duration, slightly above cdi
        if "IMA-B" in benchmark:
            return avg_ipca + 0.062  # ipca + ~6.2% (ntn-b spread)
        if "IBOVESPA" in benchmark or "SMLL" in benchmark:
            return avg_ipca + 0.085  # ipca + 8.5% (equity risk premium)
        if "IVVB11" in benchmark:
            return 0.10  # us equity historical avg
        if "IFIX" in benchmark:
            return avg_ipca + 0.055  # ipca + 5.5% (fii spread)

        return avg_cdi

    def _interpolate_annual_to_monthly(
        self,
        current_rate: float,
        annual_targets: Dict[int, float],
        horizon_months: int,
    ) -> np.ndarray:
        now = datetime.now()
        current_year = now.year
        current_month = now.month

        anchors = [(0, current_rate)]
        for year, rate in sorted(annual_targets.items()):
            months_offset = (year - current_year) * 12 + (12 - current_month)
            if months_offset > 0:
                anchors.append((months_offset, rate / 100))

        if anchors[-1][0] < horizon_months:
            anchors.append((horizon_months, anchors[-1][1]))

        anchor_months = [a[0] for a in anchors]
        anchor_rates = [a[1] for a in anchors]
        return np.interp(range(horizon_months), anchor_months, anchor_rates)


class MacroScenarioService:
    """
    lazy, cached macro scenario builder.
    fetches from bcb apis on first call, then caches for 1 hour.
    falls back gracefully to hardcoded consensus if apis are down.
    """

    def __init__(self, bcb_client: Optional[BCBApiClient] = None):
        self.client = bcb_client or BCBApiClient()
        self._cached_scenario: Optional[MacroScenario] = None
        self._cache_ts: float = 0.0
        self._cache_ttl: float = 3600.0  # 1 hour

    def build_current_scenario(self) -> MacroScenario:
        now = datetime.now().timestamp()
        if self._cached_scenario and (now - self._cache_ts) < self._cache_ttl:
            return self._cached_scenario

        scenario = self._fetch_or_fallback()
        self._cached_scenario = scenario
        self._cache_ts = now
        return scenario

    def _fetch_or_fallback(self) -> MacroScenario:
        selic = _FALLBACK["selic_current"]
        ipca = _FALLBACK["ipca_12m"]
        cdi = _FALLBACK["cdi_annual"]
        focus_selic = dict(_FALLBACK["focus_selic"])
        focus_ipca = dict(_FALLBACK["focus_ipca"])

        # try to fetch live data, but don't crash if bcb is down
        try:
            selic = self.client.get_selic_meta_current()
            logger.info(f"macro: live selic = {selic:.2f}%")
        except Exception as e:
            logger.warning(f"macro: selic fetch failed, using fallback: {e}")

        try:
            ipca = self.client.get_ipca_12m() * 100
            logger.info(f"macro: live ipca 12m = {ipca:.2f}%")
        except Exception as e:
            logger.warning(f"macro: ipca fetch failed, using fallback: {e}")

        try:
            cdi = self.client.get_cdi_current()
            logger.info(f"macro: live cdi = {cdi:.2f}%")
        except Exception as e:
            logger.warning(f"macro: cdi fetch failed, using fallback: {e}")

        try:
            data = self.client.get_focus_selic(5)
            if data:
                focus_selic = {d["year"]: d["median"] for d in data}
                logger.info(f"macro: live focus selic = {focus_selic}")
        except Exception as e:
            logger.warning(f"macro: focus selic fetch failed, using fallback: {e}")

        try:
            data = self.client.get_focus_ipca(5)
            if data:
                focus_ipca = {d["year"]: d["median"] for d in data}
                logger.info(f"macro: live focus ipca = {focus_ipca}")
        except Exception as e:
            logger.warning(f"macro: focus ipca fetch failed, using fallback: {e}")

        return MacroScenario(selic, ipca, cdi, focus_selic, focus_ipca)
