import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from urllib.parse import quote
import requests

logger = logging.getLogger(__name__)

SERIES = {
    "selic_meta": 432,
    "selic_efetiva": 11,
    "cdi": 4391,
    "ipca_mensal": 433,
    "ipca_12m": 13522,
    "igpm_mensal": 25433,
    "poupanca": 25,
}

_CACHE: Dict[str, any] = {}
_CACHE_TTL_SECONDS = 3600  # 1 hour


class BCBApiClient:
    """
    Client for Banco Central do Brasil public APIs.
    Fetches SELIC, CDI, IPCA, and FOCUS market expectations.
    """

    SGS_BASE = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{series}/dados"
    FOCUS_BASE = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata"

    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    def get_selic_meta_current(self) -> float:
        data = self._fetch_sgs_latest(SERIES["selic_meta"])
        return data["valor"]

    def get_cdi_current(self) -> float:
        selic = self.get_selic_meta_current()
        return max(0, selic - 0.10)

    def get_ipca_latest(self) -> float:
        data = self._fetch_sgs_latest(SERIES["ipca_mensal"])
        return data["valor"] / 100

    def get_ipca_12m(self) -> float:
        data = self._fetch_sgs_latest(SERIES["ipca_12m"])
        return data["valor"] / 100

    def get_focus_selic(self, years_ahead: int = 5) -> List[Dict]:
        current_year = datetime.now().year
        results = []
        for year in range(current_year, current_year + years_ahead + 1):
            try:
                data = self._fetch_focus_annual("Selic", year)
                if data:
                    latest = data[0]
                    results.append({
                        "year": year,
                        "median": latest.get("Mediana", 0),
                        "date": latest.get("Data", ""),
                    })
            except Exception as e:
                logger.warning(f"failed to fetch focus selic for {year}: {e}")
        return results

    def get_focus_ipca(self, years_ahead: int = 5) -> List[Dict]:
        current_year = datetime.now().year
        results = []
        for year in range(current_year, current_year + years_ahead + 1):
            try:
                data = self._fetch_focus_annual("IPCA", year)
                if data:
                    latest = data[0]
                    results.append({
                        "year": year,
                        "median": latest.get("Mediana", 0),
                        "date": latest.get("Data", ""),
                    })
            except Exception as e:
                logger.warning(f"failed to fetch focus ipca for {year}: {e}")
        return results


    def _fetch_sgs_latest(self, series_id: int) -> Dict:
        cache_key = f"sgs_latest_{series_id}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        url = f"{self.SGS_BASE.format(series=series_id)}/ultimos/1?formato=json"
        data = self._http_get_json(url)
        if data and len(data) > 0:
            result = {
                "valor": float(data[0]["valor"]),
                "data": data[0]["data"],
            }
            self._set_cached(cache_key, result)
            return result
        raise RuntimeError(f"no data returned for sgs series {series_id}")

    def _fetch_sgs_period(self, series_id: int, months: int) -> List[Dict]:
        cache_key = f"sgs_period_{series_id}_{months}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        end = datetime.now()
        start = end - timedelta(days=months * 31)
        date_fmt = "%d/%m/%Y"
        url = (
            f"{self.SGS_BASE.format(series=series_id)}"
            f"?formato=json&dataInicial={start.strftime(date_fmt)}&dataFinal={end.strftime(date_fmt)}"
        )
        data = self._http_get_json(url)
        result = [{"data": d["data"], "valor": float(d["valor"])} for d in (data or [])]
        self._set_cached(cache_key, result)
        return result

    def _fetch_focus_annual(self, indicator: str, year: int) -> List[Dict]:
        cache_key = f"focus_{indicator}_{year}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        filter_str = f"Indicador eq '{indicator}' and DataReferencia eq '{year}'"
        encoded_filter = quote(filter_str)
        url = f"{self.FOCUS_BASE}/ExpectativasMercadoAnuais?$filter={encoded_filter}&$orderby=Data%20desc&$top=5&$format=json"
        data = self._http_get_json(url)
        result = data.get("value", []) if isinstance(data, dict) else []
        self._set_cached(cache_key, result)
        return result

    def _http_get_json(self, url: str) -> any:
        headers = {
            "Accept": "application/json",
            "User-Agent": "ProInvestAI/1.0",
        }
        try:
            resp = requests.get(url, headers=headers, timeout=self.timeout)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"request error for {url}: {e}")
            raise

    def _get_cached(self, key: str) -> any:
        if key in _CACHE:
            entry = _CACHE[key]
            if datetime.now().timestamp() - entry["ts"] < _CACHE_TTL_SECONDS:
                return entry["value"]
        return None

    def _set_cached(self, key: str, value: any) -> None:
        _CACHE[key] = {"value": value, "ts": datetime.now().timestamp()}
