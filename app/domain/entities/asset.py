from enum import Enum
from dataclasses import dataclass
from decimal import Decimal


class AssetClass(str, Enum):
    """asset classes aligned with institutional committee standards."""
    FIXED_INCOME = "fixed_income"
    EQUITY = "equity"
    REAL_ESTATE = "real_estate"
    MULTIMERCADO = "multimercado"
    INTERNATIONAL = "international"
    STRUCTURED = "structured"
    CASH = "cash"


class Benchmark(str, Enum):
    """benchmark indices used by institutional committees."""
    # renda fixa
    CDI = "CDI"
    SELIC = "SELIC"
    IPCA = "IPCA"
    IRF_M = "IRF-M"
    IRF_M1 = "IRF-M 1"
    IMA_B = "IMA-B"
    IMA_B5 = "IMA-B 5"
    IMA_B5_PLUS = "IMA-B 5+"
    IMA_GERAL = "IMA Geral"
    IMA_GERAL_EX_C = "IMA Geral ex-C"
    IDKA_IPCA_2A = "IDKA IPCA 2A"
    # renda variavel
    IBOVESPA = "IBOVESPA"
    IBRX_100 = "IBrX-100"
    SMLL = "SMLL"
    IDIV = "IDIV"
    # multimercado
    IHFA = "IHFA"
    # imobiliario
    IFIX = "IFIX"
    # meta atuarial
    META_ATUARIAL = "Meta Atuarial"


@dataclass
class Asset:
    name: str
    asset_class: AssetClass
    subclass: str
    benchmark: str
    spread: Decimal
    tax_exempt: bool
    min_investment: Decimal
    liquidity_days: int
    ticker: str | None = None
    historical_returns: list[Decimal] | None = None
