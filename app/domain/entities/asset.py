"""
asset entity — represents a single investable product in the brazilian market.

each asset has real-world properties: expected return (dynamic via bcb focus),
volatility, tax treatment (ir regressivo or exempt), liquidity, custody costs,
and risk classification.

this is NOT a benchmark index — it's a product the investor actually buys.
"""

from dataclasses import dataclass
from enum import Enum


class AssetType(Enum):
    """classification of investable asset types in the brazilian market."""

    # renda fixa — pos-fixado
    TESOURO_SELIC = "tesouro_selic"
    CDB_LIQUIDEZ = "cdb_liquidez_diaria"
    LCI_LCA = "lci_lca"

    # renda fixa — inflacao
    TESOURO_IPCA = "tesouro_ipca"
    TESOURO_IPCA_JUROS = "tesouro_ipca_juros_semestrais"
    DEBENTURE_INCENTIVADA = "debenture_incentivada"

    # renda fixa — prefixado
    TESOURO_PREFIXADO = "tesouro_prefixado"
    CDB_PREFIXADO = "cdb_prefixado"

    # fundos imobiliarios
    FII = "fundo_imobiliario"

    # renda variavel — brasil
    ETF_IBOV = "etf_ibovespa"
    ETF_SMALL_CAPS = "etf_small_caps"
    ACAO_DIVIDENDOS = "acao_dividendos"

    # internacional
    ETF_SP500 = "etf_sp500"

    # previdencia
    PREVIDENCIA_PGBL = "previdencia_pgbl"

    # alternativo
    CRIPTO_BTC = "cripto_btc"


class AssetClass(str, Enum):
    """high-level asset class grouping."""

    RENDA_FIXA = "renda_fixa"
    FII = "fii"
    RENDA_VARIAVEL = "renda_variavel"
    INTERNACIONAL = "internacional"
    PREVIDENCIA = "previdencia"
    ALTERNATIVO = "alternativo"


# mapping from asset type to class
ASSET_TYPE_TO_CLASS = {
    AssetType.TESOURO_SELIC: AssetClass.RENDA_FIXA,
    AssetType.CDB_LIQUIDEZ: AssetClass.RENDA_FIXA,
    AssetType.LCI_LCA: AssetClass.RENDA_FIXA,
    AssetType.TESOURO_IPCA: AssetClass.RENDA_FIXA,
    AssetType.TESOURO_IPCA_JUROS: AssetClass.RENDA_FIXA,
    AssetType.DEBENTURE_INCENTIVADA: AssetClass.RENDA_FIXA,
    AssetType.TESOURO_PREFIXADO: AssetClass.RENDA_FIXA,
    AssetType.CDB_PREFIXADO: AssetClass.RENDA_FIXA,
    AssetType.FII: AssetClass.FII,
    AssetType.ETF_IBOV: AssetClass.RENDA_VARIAVEL,
    AssetType.ETF_SMALL_CAPS: AssetClass.RENDA_VARIAVEL,
    AssetType.ACAO_DIVIDENDOS: AssetClass.RENDA_VARIAVEL,
    AssetType.ETF_SP500: AssetClass.INTERNACIONAL,
    AssetType.PREVIDENCIA_PGBL: AssetClass.PREVIDENCIA,
    AssetType.CRIPTO_BTC: AssetClass.ALTERNATIVO,
}


@dataclass(frozen=True)
class Asset:
    """
    represents an investable product with its expected return and risk profile.

    all return/volatility values are annualized decimals (e.g. 0.1475 = 14.75%).
    """

    name: str
    asset_type: AssetType
    expected_annual_return: float
    annual_volatility: float
    is_tax_exempt: bool = False
    min_holding_days: int = 0
    liquidity_days: int = 1
    description: str = ""
    has_fgc: bool = False
    b3_custody_rate: float = 0.0
    coupon_frequency: str | None = None

    @property
    def asset_class(self) -> AssetClass:
        return ASSET_TYPE_TO_CLASS.get(self.asset_type, AssetClass.RENDA_FIXA)

    @property
    def expected_monthly_return(self) -> float:
        """convert annual return to monthly (compound)."""
        return (1 + self.expected_annual_return) ** (1 / 12) - 1

    @property
    def monthly_volatility(self) -> float:
        """convert annual volatility to monthly."""
        return self.annual_volatility / (12 ** 0.5)

    @property
    def risk_category(self) -> str:
        """classify risk based on annual volatility."""
        if self.annual_volatility <= 0.02:
            return "muito_baixo"
        elif self.annual_volatility <= 0.05:
            return "baixo"
        elif self.annual_volatility <= 0.15:
            return "moderado"
        elif self.annual_volatility <= 0.30:
            return "alto"
        else:
            return "muito_alto"

    @property
    def risk_label(self) -> str:
        """human-readable risk label in portuguese."""
        labels = {
            "muito_baixo": "Muito Baixo",
            "baixo": "Baixo",
            "moderado": "Moderado",
            "alto": "Alto",
            "muito_alto": "Muito Alto",
        }
        return labels.get(self.risk_category, "Desconhecido")

    @property
    def is_liquid(self) -> bool:
        """whether the asset can be redeemed within 1 business day."""
        return self.liquidity_days <= 1 and self.annual_volatility <= 0.02

    @property
    def is_variable_income(self) -> bool:
        """whether the asset is classified as variable income (renda variavel)."""
        return self.asset_class in (
            AssetClass.RENDA_VARIAVEL,
            AssetClass.FII,
            AssetClass.INTERNACIONAL,
            AssetClass.ALTERNATIVO,
        )

    def __post_init__(self):
        if self.expected_annual_return < -1.0:
            raise ValueError("expected annual return cannot be less than -100%")
        if self.annual_volatility < 0:
            raise ValueError("annual volatility must be non-negative")
