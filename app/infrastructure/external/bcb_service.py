import logging
from datetime import datetime
from typing import Dict, List, Optional
import numpy as np
from .bcb_api import BCBApiClient

logger = logging.getLogger(__name__)


class BCBService:
    """
    Fetches and manages historical data from BCB.
    """

    def __init__(self, client: Optional[BCBApiClient] = None):
        self.client = client or BCBApiClient()

    def get_cdi_monthly_returns(self, start_year: int = 2010) -> Dict[str, float]:
        # Series 4391 is daily CDI accumulated monthly
        # For simplicity in this version, we fetch a period and accumulate
        start_date = f"01/01/{start_year}"
        end_date = datetime.now().strftime("%d/%m/%Y")
        url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.4391/dados?formato=json&dataInicial={start_date}&dataFinal={end_date}"
        
        try:
            data = self.client._http_get_json(url)
            return self._accumulate_daily_to_monthly(data)
        except Exception as e:
            logger.error(f"Failed to fetch CDI history: {e}")
            return {}

    def get_ipca_monthly(self, start_year: int = 2010) -> Dict[str, float]:
        start_date = f"01/01/{start_year}"
        end_date = datetime.now().strftime("%d/%m/%Y")
        url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=json&dataInicial={start_date}&dataFinal={end_date}"
        
        try:
            data = self.client._http_get_json(url)
            monthly = {}
            for d in data:
                dt = datetime.strptime(d["data"], "%d/%m/%Y")
                key = dt.strftime("%Y-%m")
                monthly[key] = float(d["valor"]) / 100
            return monthly
        except Exception as e:
            logger.error(f"Failed to fetch IPCA history: {e}")
            return {}

    def build_asset_return_series(self, start_year: int = 2015) -> Dict[str, Dict[str, float]]:
        cdi = self.get_cdi_monthly_returns(start_year)
        ipca = self.get_ipca_monthly(start_year)
        
        common_months = sorted(set(cdi.keys()) & set(ipca.keys()))
        if not common_months:
            return {}

        result = {}
        for month in common_months:
            cdi_ret = cdi.get(month, 0)
            ipca_ret = ipca.get(month, 0)

            # Map to expected asset types in the system
            for asset_type, ret in [
                ("fixed_income_post", cdi_ret),
                ("fixed_income_ipca", ipca_ret + ((1 + 0.06) ** (1/12) - 1)), # IPCA + 6%
                ("fixed_income_pre", cdi_ret * 1.1),
                ("equity", cdi_ret + 0.01), # Placeholder for equity if no Ibov
            ]:
                if asset_type not in result:
                    result[asset_type] = {}
                result[asset_type][month] = ret
        
        return result

    def get_crisis_periods(self) -> List[Dict]:
        return [
            {"name": "COVID-19 Crash", "start": "2020-02", "end": "2020-04", "severity": "extreme"},
            {"name": "Joesley Day", "start": "2017-05", "end": "2017-08", "severity": "high"},
            {"name": "Alta Selic 2021-2022", "start": "2021-03", "end": "2022-08", "severity": "high"},
        ]

    def _accumulate_daily_to_monthly(self, daily_data: List[Dict]) -> Dict[str, float]:
        monthly_factors = {}
        for d in daily_data:
            dt = datetime.strptime(d["data"], "%d/%m/%Y")
            key = dt.strftime("%Y-%m")
            daily_rate = float(d["valor"]) / 100
            if key not in monthly_factors:
                monthly_factors[key] = 1.0
            monthly_factors[key] *= (1 + daily_rate)
        return {k: v - 1 for k, v in monthly_factors.items()}
