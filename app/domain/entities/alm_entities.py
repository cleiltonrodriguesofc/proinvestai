"""
alm (asset-liability management) domain entities.

these entities model the core concepts of an rpps alm study,
following the methodology used by lema economia & finanças.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


# ---------------------------------------------------------------------------
# enums
# ---------------------------------------------------------------------------

class AssetSegment(str, Enum):
    """segments defined by cmn 5.272/2025, art. 2."""
    RENDA_FIXA = "renda_fixa"
    RENDA_VARIAVEL = "renda_variavel"
    EXTERIOR = "exterior"
    ESTRUTURADOS = "estruturados"
    FUNDOS_IMOBILIARIOS = "fundos_imobiliarios"
    EMPRESTIMOS_CONSIGNADOS = "emprestimos_consignados"


class RegulatoryArticle(str, Enum):
    """enquadramento per cmn 5.272/2025."""
    ART_7_I = "7, I"      # fi rf 100% tp
    ART_7_II = "7, II"    # títulos tn direto (selic)
    ART_7_III = "7, III"  # títulos tn balcão (nível I+)
    ART_7_IV = "7, IV"    # compromissadas (nível I+)
    ART_7_V = "7, V"      # fi rf / etf rf sem cp (nível II+)
    ART_7_VI = "7, VI"    # ativos bancários (nível II+)
    ART_7_VII = "7, VII"  # crédito privado (nível III+)
    ART_7_VIII = "7, VIII"  # debêntures infra (nível III+)
    ART_7_IX = "7, IX"    # fidc sênior (nível IV)
    ART_8_I = "8, I"      # fi ações (nível II+)
    ART_8_II = "8, II"    # etf ações (nível II+)
    ART_8_III = "8, III"  # bdr (nível III+)
    ART_8_IV = "8, IV"    # etf internacional (nível III+)
    ART_9_I = "9, I"      # rf dívida externa (nível III+)
    ART_9_II = "9, II"    # exterior qualificado (nível III+)
    ART_9_III = "9, III"  # exterior geral (nível III+)
    ART_10_I = "10, I"    # multimercado (nível II+)
    ART_10_II = "10, II"  # fiagro (nível III+)
    ART_10_III = "10, III"  # fip (nível IV)
    ART_10_IV = "10, IV"  # ações mercado acesso (nível IV)
    ART_11 = "11"         # fii (nível III+)
    ART_12 = "12"         # empréstimos consignados


class ProjectionModel(str, Enum):
    """models used to project index returns."""
    ETTJ_ANBIMA = "ettj_anbima"
    HISTORICAL_60M = "historical_60m"
    CDI_SPREAD = "cdi_spread"
    WEIGHTED_COUPON = "weighted_coupon"
    MANUAL = "manual"


# ---------------------------------------------------------------------------
# value objects
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CashFlowYear:
    """single year in the actuarial flow projection (cadprev format)."""
    instant: int
    year: int
    discount_rate: float
    discount_factor: float
    contribution_base: float
    total_revenues: float
    total_expenditures: float
    financial_result: float        # (A) - (B)
    accumulated_balance_pv: float  # saldo acumulado a valor presente
    expected_return_pct: float
    asset_return: float
    guaranteed_resources: float

    @property
    def net_flow(self) -> float:
        """revenues minus expenditures (receitas - despesas)."""
        return self.total_revenues - self.total_expenditures


@dataclass(frozen=True)
class AssetIndex:
    """market index with projected return and volatility."""
    name: str
    segment: AssetSegment
    regulatory_article: RegulatoryArticle
    projected_real_return: float   # % a.a. (real, above inflation)
    volatility: float              # % a.a. (annual std dev)
    projection_model: ProjectionModel
    min_weight: float = 0.0        # minimum allocation constraint
    max_weight: float = 1.0        # maximum allocation constraint
    is_locked: bool = False        # true for illiquid/vértice positions


@dataclass(frozen=True)
class BondAllocation:
    """ntn-b allocation matched to a liability period."""
    period: str           # e.g. "2028-2029", "2030-2034"
    pv_flows: float       # present value of deficit flows in period
    weight_portfolio: float  # weight within bond sub-portfolio
    weight_total: float   # weight of total patrimony
    bond_name: str        # e.g. "NTNB 2030"
    rate: float           # indicative rate at reference date


# ---------------------------------------------------------------------------
# entities
# ---------------------------------------------------------------------------

@dataclass
class PortfolioHolding:
    """single position in the current rpps portfolio."""
    fund_name: str
    balance: float
    weight: float           # % of total
    benchmark: str          # e.g. "IRF-M 1", "CDI", "IBOVESPA"
    regulatory_article: RegulatoryArticle
    segment: AssetSegment
    liquidity_days: int     # d+0, d+1, d+3
    maturity_date: str | None = None  # for vértice funds
    admin_fee: float = 0.0  # taxa de administração (% a.a.)
    monthly_return: float = 0.0  # last month return (%)
    is_legacy: bool = False  # true if pre-5.272 position that exceeds new limits


@dataclass
class CurrentPortfolio:
    """complete current portfolio of the rpps."""
    reference_date: str
    total_patrimony: float
    cash_balance: float
    holdings: list[PortfolioHolding] = field(default_factory=list)

    @property
    def total_invested(self) -> float:
        return sum(h.balance for h in self.holdings)

    @property
    def segment_breakdown(self) -> dict[str, float]:
        """returns {segment: total_balance}."""
        result: dict[str, float] = {}
        for h in self.holdings:
            key = h.segment.value
            result[key] = result.get(key, 0.0) + h.balance
        return result

    @property
    def benchmark_breakdown(self) -> dict[str, float]:
        """returns {benchmark: total_balance}."""
        result: dict[str, float] = {}
        for h in self.holdings:
            result[h.benchmark] = result.get(h.benchmark, 0.0) + h.balance
        return result

    @property
    def legacy_balance(self) -> float:
        """total balance in legacy positions (pre-5.272 that exceed limits)."""
        return sum(h.balance for h in self.holdings if h.is_legacy)


@dataclass
class OptimizedPortfolio:
    """single point on the efficient frontier."""
    portfolio_id: int
    expected_return: float   # % a.a. real
    volatility: float        # % a.a.
    sharpe_ratio: float
    weights: dict[str, float]  # index_name -> weight (0-1)

    def weight_for(self, index_name: str) -> float:
        return self.weights.get(index_name, 0.0)


@dataclass
class SolvencyResult:
    """aggregate statistics from monte carlo solvency analysis."""
    portfolio_id: int
    n_scenarios: int
    n_years: int

    # return statistics
    pct_positive_returns: float
    min_return: float
    mean_return: float
    max_return: float

    # funding ratio statistics
    pct_solvent: float              # % of (scenario, year) with FR >= 1
    mean_funding_ratio: float
    quantile_5_funding_ratio: float

    # raw data for charting
    yearly_median_patrimony: list[float] = field(default_factory=list)
    yearly_median_funding_ratio: list[float] = field(default_factory=list)


@dataclass
class ALMResult:
    """complete result of an alm study."""
    # metadata
    rpps_name: str
    reference_date: str
    actuarial_rate: float         # taxa de juros atuarial (e.g. 5.69%)

    # inputs
    current_portfolio: CurrentPortfolio
    cashflows: list[CashFlowYear]
    indices: list[AssetIndex]

    # computed results
    patrimony: float
    required_return: float        # taxa de equilíbrio real
    npv_deficit_flows: float      # vpl dos fluxos deficitários
    meta_atuarial: float          # ipca + taxa atuarial

    # optimization
    efficient_frontier: list[OptimizedPortfolio] = field(default_factory=list)
    recommended_portfolio: OptimizedPortfolio | None = None
    bond_allocations: list[BondAllocation] = field(default_factory=list)

    # solvency
    solvency_results: list[SolvencyResult] = field(default_factory=list)

    # gap analysis (current vs recommended)
    gap_table: dict[str, dict[str, float]] = field(default_factory=dict)
