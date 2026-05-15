"""
portfolio builder — constructs optimized portfolios with real investable products.

ported from the original 'investimento ana' engine and expanded to support
all investor profiles (conservative, moderate, aggressive).

key features:
  - dynamic asset catalog with yields from bcb focus projections
  - markowitz optimization with real constraints per profile
  - emergency reserve as a hard constraint
  - ir regressivo, b3 custody, and fgc coverage awareness
  - forward projections using selic/ipca trajectory from focus
"""

import logging
import numpy as np
from typing import Dict, List, Optional

from ...domain.entities.asset import Asset, AssetType, AssetClass
from ...domain.entities.portfolio import Portfolio
from ...domain.value_objects.allocation import Allocation
from ...infrastructure.external.macro_scenario_service import MacroScenario

logger = logging.getLogger(__name__)

# asset categories for markowitz constraints
ASSET_CATEGORIES = {
    "tesouro_selic": "liquid",
    "cdb_liquidez": "liquid",
    "lci_lca": "fixed_income",
    "tesouro_ipca": "fixed_income",
    "tesouro_ipca_juros": "fixed_income",
    "debenture_incentivada": "fixed_income",
    "tesouro_prefixado": "fixed_income",
    "cdb_prefixado": "fixed_income",
    "fii": "equity",
    "etf_ibov": "equity",
    "etf_small_caps": "equity",
    "acao_dividendos": "equity",
    "etf_sp500": "equity",
    "previdencia_pgbl": "fixed_income",
    "cripto_btc": "equity",
}

# profile constraints
PROFILE_CONSTRAINTS = {
    "conservative": {
        "max_variable_income_pct": 0.05,
        "reserve_months": 12,
        "min_liquid_pct": 0.35,
        "max_international_pct": 0.00,
        "max_crypto_pct": 0.00,
        "max_single_asset_pct": 0.40,
        "allowed_types": [
            "tesouro_selic", "cdb_liquidez", "lci_lca",
            "tesouro_ipca", "tesouro_ipca_juros",
            "tesouro_prefixado", "cdb_prefixado",
            "debenture_incentivada",
        ],
    },
    "moderate": {
        "max_variable_income_pct": 0.20,
        "reserve_months": 6,
        "min_liquid_pct": 0.20,
        "max_international_pct": 0.10,
        "max_crypto_pct": 0.00,
        "max_single_asset_pct": 0.35,
        "allowed_types": [
            "tesouro_selic", "cdb_liquidez", "lci_lca",
            "tesouro_ipca", "tesouro_ipca_juros",
            "tesouro_prefixado", "cdb_prefixado",
            "debenture_incentivada",
            "fii", "etf_ibov", "etf_sp500",
            "previdencia_pgbl",
        ],
    },
    "aggressive": {
        "max_variable_income_pct": 0.40,
        "reserve_months": 3,
        "min_liquid_pct": 0.10,
        "max_international_pct": 0.20,
        "max_crypto_pct": 0.05,
        "max_single_asset_pct": 0.30,
        "allowed_types": [
            "tesouro_selic", "cdb_liquidez", "lci_lca",
            "tesouro_ipca", "tesouro_ipca_juros",
            "tesouro_prefixado", "cdb_prefixado",
            "debenture_incentivada",
            "fii", "etf_ibov", "etf_small_caps",
            "acao_dividendos", "etf_sp500",
            "previdencia_pgbl", "cripto_btc",
        ],
    },
}


def build_asset_catalog(macro: MacroScenario, profile: str = "moderate") -> Dict[str, Asset]:
    """
    build a catalog of real investable products with dynamic yields from focus.

    yields are calibrated to the current macro environment:
    - selic-linked products use the live selic rate
    - ipca-linked products use the live ipca + real spread
    - cdi-linked products use the live cdi rate
    """
    h = 120  # 10-year horizon for rate projection
    selic_0 = macro.build_selic_path(h)[0]
    ipca_0 = macro.build_ipca_path(h)[0]
    cdi_0 = macro.build_cdi_path(h)[0]

    constraints = PROFILE_CONSTRAINTS.get(profile, PROFILE_CONSTRAINTS["moderate"])
    allowed = constraints["allowed_types"]

    # full catalog — only include assets allowed for this profile
    all_assets = {
        "tesouro_selic": Asset(
            name="Tesouro Selic 2031",
            asset_type=AssetType.TESOURO_SELIC,
            expected_annual_return=selic_0 + 0.0008,
            annual_volatility=0.005,
            is_tax_exempt=False, min_holding_days=0, liquidity_days=1,
            has_fgc=False, b3_custody_rate=0.002,
            description=f"Titulo publico que acompanha a taxa Selic ({selic_0:.2%}). "
                        f"O investimento mais seguro do Brasil. Ideal para reserva de emergencia.",
        ),
        "cdb_liquidez": Asset(
            name="CDB Liquidez Diaria 100% CDI",
            asset_type=AssetType.CDB_LIQUIDEZ,
            expected_annual_return=cdi_0,
            annual_volatility=0.005,
            is_tax_exempt=False, min_holding_days=0, liquidity_days=0,
            has_fgc=True, b3_custody_rate=0.0,
            description=f"Certificado de deposito bancario com liquidez imediata. "
                        f"Rende 100% do CDI ({cdi_0:.2%}). Protegido pelo FGC ate R$250 mil.",
        ),
        "lci_lca": Asset(
            name="LCI/LCA 93% CDI",
            asset_type=AssetType.LCI_LCA,
            expected_annual_return=cdi_0 * 0.93,
            annual_volatility=0.005,
            is_tax_exempt=True, min_holding_days=90, liquidity_days=90,
            has_fgc=True, b3_custody_rate=0.0,
            description=f"Letra de credito isenta de imposto de renda. "
                        f"Rende 93% do CDI = {cdi_0 * 0.93:.2%}, mas como eh isento, "
                        f"o retorno liquido supera CDBs tributados. FGC ate R$250 mil.",
        ),
        "tesouro_ipca": Asset(
            name="Tesouro IPCA+ 2032",
            asset_type=AssetType.TESOURO_IPCA,
            expected_annual_return=ipca_0 + 0.0761,
            annual_volatility=0.08,
            is_tax_exempt=False, min_holding_days=365, liquidity_days=1,
            has_fgc=False, b3_custody_rate=0.002,
            description=f"Titulo publico que paga inflacao (IPCA {ipca_0:.2%}) + 7,61% real. "
                        f"Protege seu poder de compra a longo prazo. "
                        f"ATENCAO: pode oscilar se vendido antes do vencimento (marcacao a mercado).",
        ),
        "tesouro_ipca_juros": Asset(
            name="Tesouro IPCA+ Juros Semestrais 2037",
            asset_type=AssetType.TESOURO_IPCA_JUROS,
            expected_annual_return=ipca_0 + 0.0738,
            annual_volatility=0.06,
            is_tax_exempt=False, min_holding_days=365, liquidity_days=1,
            has_fgc=False, b3_custody_rate=0.002,
            coupon_frequency="semestral",
            description=f"Titulo que paga cupons de juros em janeiro e julho. "
                        f"Rende IPCA ({ipca_0:.2%}) + 7,38%. "
                        f"Ideal para quem busca renda periodica.",
        ),
        "debenture_incentivada": Asset(
            name="Debenture Incentivada IPCA+ 7,0%",
            asset_type=AssetType.DEBENTURE_INCENTIVADA,
            expected_annual_return=ipca_0 + 0.07,
            annual_volatility=0.07,
            is_tax_exempt=True, min_holding_days=720, liquidity_days=30,
            has_fgc=False, b3_custody_rate=0.0,
            description=f"Titulo de divida de empresa de infraestrutura. "
                        f"Isento de imposto de renda para pessoa fisica. "
                        f"Rende IPCA + 7,0%. Risco de credito maior que Tesouro.",
        ),
        "tesouro_prefixado": Asset(
            name="Tesouro Prefixado 2028",
            asset_type=AssetType.TESOURO_PREFIXADO,
            expected_annual_return=cdi_0 * 0.98,
            annual_volatility=0.04,
            is_tax_exempt=False, min_holding_days=365, liquidity_days=1,
            has_fgc=False, b3_custody_rate=0.002,
            description=f"Titulo com rentabilidade definida na compra. "
                        f"Voce sabe exatamente quanto vai receber no vencimento. "
                        f"ATENCAO: se a Selic subir, o preco cai (marcacao a mercado).",
        ),
        "cdb_prefixado": Asset(
            name=f"CDB Prefixado {cdi_0 * 1.10:.1%} a.a.",
            asset_type=AssetType.CDB_PREFIXADO,
            expected_annual_return=cdi_0 * 1.10,
            annual_volatility=0.01,
            is_tax_exempt=False, min_holding_days=360, liquidity_days=360,
            has_fgc=True, b3_custody_rate=0.0,
            description=f"CDB com taxa fixa de {cdi_0 * 1.10:.2%} ao ano. "
                        f"FGC ate R$250 mil. Sem liquidez ate o vencimento (D+360).",
        ),
        "fii": Asset(
            name="IFIX (Fundos Imobiliarios)",
            asset_type=AssetType.FII,
            expected_annual_return=ipca_0 + 0.055,
            annual_volatility=0.12,
            is_tax_exempt=True, min_holding_days=0, liquidity_days=3,
            has_fgc=False, b3_custody_rate=0.0,
            description=f"Fundos que investem em imoveis comerciais. "
                        f"Pagam dividendos mensais isentos de IR. "
                        f"Preco das cotas oscila na bolsa (renda variavel).",
        ),
        "etf_ibov": Asset(
            name="ETF Ibovespa (BOVA11)",
            asset_type=AssetType.ETF_IBOV,
            expected_annual_return=ipca_0 + 0.085,
            annual_volatility=0.22,
            is_tax_exempt=False, min_holding_days=0, liquidity_days=3,
            has_fgc=False, b3_custody_rate=0.0,
            description=f"Fundo que replica o indice Ibovespa (ações das maiores empresas). "
                        f"Historicamente rende IPCA + 8,5% no longo prazo, "
                        f"mas pode cair 30-50% em crises.",
        ),
        "etf_small_caps": Asset(
            name="ETF Small Caps (SMAL11)",
            asset_type=AssetType.ETF_SMALL_CAPS,
            expected_annual_return=ipca_0 + 0.10,
            annual_volatility=0.28,
            is_tax_exempt=False, min_holding_days=0, liquidity_days=3,
            has_fgc=False, b3_custody_rate=0.0,
            description=f"Fundo que investe em empresas menores da bolsa. "
                        f"Potencial de retorno maior, mas risco muito alto. "
                        f"Pode cair mais de 50% em crises.",
        ),
        "acao_dividendos": Asset(
            name="Acoes de Dividendos (IDIV)",
            asset_type=AssetType.ACAO_DIVIDENDOS,
            expected_annual_return=ipca_0 + 0.09,
            annual_volatility=0.20,
            is_tax_exempt=False, min_holding_days=0, liquidity_days=3,
            has_fgc=False, b3_custody_rate=0.0,
            description=f"Empresas que pagam dividendos consistentes. "
                        f"Renda periodica + potencial de valorizacao. "
                        f"Menos volatil que o Ibovespa geral.",
        ),
        "etf_sp500": Asset(
            name="ETF S&P 500 (IVVB11)",
            asset_type=AssetType.ETF_SP500,
            expected_annual_return=0.10,
            annual_volatility=0.18,
            is_tax_exempt=False, min_holding_days=0, liquidity_days=3,
            has_fgc=False, b3_custody_rate=0.0,
            description="Fundo que replica as 500 maiores empresas dos EUA. "
                        "Diversificacao internacional + exposicao ao dolar. "
                        "Historicamente rende ~10% ao ano em dolares.",
        ),
        "previdencia_pgbl": Asset(
            name="Previdencia PGBL RF",
            asset_type=AssetType.PREVIDENCIA_PGBL,
            expected_annual_return=cdi_0 * 0.95,
            annual_volatility=0.02,
            is_tax_exempt=False, min_holding_days=0, liquidity_days=60,
            has_fgc=False, b3_custody_rate=0.0,
            description=f"Previdencia privada com beneficio fiscal. "
                        f"Permite deduzir ate 12% da renda bruta no IR. "
                        f"Rende ~95% CDI. Ideal para quem faz declaracao completa.",
        ),
        "cripto_btc": Asset(
            name="Bitcoin (via ETF HASH11)",
            asset_type=AssetType.CRIPTO_BTC,
            expected_annual_return=0.25,
            annual_volatility=0.65,
            is_tax_exempt=False, min_holding_days=0, liquidity_days=3,
            has_fgc=False, b3_custody_rate=0.0,
            description="Exposicao a criptomoedas via ETF na B3. "
                        "Potencial de retorno muito alto, mas risco extremo. "
                        "Pode cair 70-80% em bear markets.",
        ),
    }

    # filter to only allowed assets for this profile
    catalog = {k: v for k, v in all_assets.items() if k in allowed}

    logger.info(
        f"asset catalog built for '{profile}': {len(catalog)} products "
        f"(selic={selic_0:.2%}, cdi={cdi_0:.2%}, ipca={ipca_0:.2%})"
    )
    return catalog


def build_optimized_portfolio(
    catalog: Dict[str, Asset],
    total_value: float,
    monthly_expenses: float,
    profile: str,
    macro: MacroScenario,
    historical_returns: Optional[Dict[str, np.ndarray]] = None,
) -> Portfolio:
    """
    build a markowitz-optimized portfolio with real constraints.

    constraints per profile:
      - emergency reserve (liquid assets >= expenses * months)
      - max variable income percentage
      - max single asset concentration
      - no short selling
    """
    constraints = PROFILE_CONSTRAINTS.get(profile, PROFILE_CONSTRAINTS["moderate"])
    reserve_months = constraints["reserve_months"]

    # compute reserve constraint
    if monthly_expenses > 0:
        reserve = monthly_expenses * reserve_months
        min_liquid_pct = min(reserve / total_value, 0.55)
    else:
        min_liquid_pct = constraints["min_liquid_pct"]

    asset_keys = list(catalog.keys())
    n_assets = len(asset_keys)

    if n_assets < 2:
        logger.warning("not enough assets for optimization, using heuristic")
        return _build_heuristic_portfolio(
            catalog, total_value, monthly_expenses, reserve_months, profile
        )

    # try markowitz if we have historical data
    if historical_returns and len(historical_returns) >= 3:
        return _build_markowitz_portfolio(
            catalog, total_value, monthly_expenses, reserve_months,
            profile, constraints, historical_returns, macro,
        )

    # fallback to heuristic
    logger.info("no historical data for markowitz, using heuristic allocation")
    return _build_heuristic_portfolio(
        catalog, total_value, monthly_expenses, reserve_months, profile
    )


def _build_markowitz_portfolio(
    catalog: Dict[str, Asset],
    total_value: float,
    monthly_expenses: float,
    reserve_months: int,
    profile: str,
    constraints: dict,
    historical_returns: Dict[str, np.ndarray],
    macro: MacroScenario,
) -> Portfolio:
    """build portfolio using markowitz mean-variance optimization."""
    from .markowitz_optimizer import MarkowitzOptimizer

    asset_keys = [k for k in catalog.keys() if k in historical_returns]
    if len(asset_keys) < 3:
        return _build_heuristic_portfolio(
            catalog, total_value, monthly_expenses, reserve_months, profile
        )

    # align historical data
    min_len = min(len(historical_returns[k]) for k in asset_keys)
    returns_matrix = np.column_stack([
        historical_returns[k][:min_len] for k in asset_keys
    ])
    monthly_cov = np.cov(returns_matrix, rowvar=False)
    annual_cov = monthly_cov * 12

    # expected returns from focus (forward-looking)
    expected_returns = np.array([
        catalog[k].expected_annual_return for k in asset_keys
    ])

    # build category map for optimizer
    categories = {k: ASSET_CATEGORIES.get(k, "fixed_income") for k in asset_keys}

    optimizer = MarkowitzOptimizer(
        asset_names=asset_keys,
        expected_returns=expected_returns,
        covariance_matrix=annual_cov,
        asset_categories=categories,
        risk_free_rate=macro.cdi_annual / 100,
    )

    # compute liquid constraint
    if monthly_expenses > 0:
        reserve = monthly_expenses * reserve_months
        min_liquid_pct = min(reserve / total_value, 0.55)
    else:
        min_liquid_pct = constraints["min_liquid_pct"]

    # max weights per asset
    max_w = {k: constraints["max_single_asset_pct"] for k in asset_keys}

    # run optimization
    opt_result = optimizer.optimize_max_sharpe(
        max_weights=max_w,
        min_liquid_pct=min_liquid_pct,
        max_variable_income_pct=constraints["max_variable_income_pct"],
    )

    logger.info(
        f"markowitz max_sharpe ({profile}): "
        f"ret={opt_result.expected_return:.2%}, "
        f"vol={opt_result.expected_volatility:.2%}, "
        f"sharpe={opt_result.sharpe_ratio:.2f}"
    )

    # build portfolio from optimized weights
    portfolio = Portfolio(
        name=f"Carteira {profile.capitalize()}",
        total_value=total_value,
        monthly_expenses=monthly_expenses,
        reserve_months=reserve_months,
        rebalancing_months=3,
        description=(
            f"Markowitz Max Sharpe | "
            f"ret={opt_result.expected_return:.2%} "
            f"vol={opt_result.expected_volatility:.2%} "
            f"sharpe={opt_result.sharpe_ratio:.2f}"
        ),
    )

    for key in asset_keys:
        w = opt_result.weights.get(key, 0)
        if w >= 0.005:
            rounded = round(w, 4)
            if rounded > 0:
                portfolio.add_allocation(catalog[key], rounded)

    # fix rounding: add remainder to largest liquid asset
    gap = round(1.0 - portfolio.total_allocation_pct, 4)
    if gap > 0.001 and "tesouro_selic" in catalog:
        portfolio.add_allocation(catalog["tesouro_selic"], gap)

    return portfolio


def _build_heuristic_portfolio(
    catalog: Dict[str, Asset],
    total_value: float,
    monthly_expenses: float,
    reserve_months: int,
    profile: str,
) -> Portfolio:
    """fallback heuristic allocation when markowitz data is unavailable."""
    constraints = PROFILE_CONSTRAINTS.get(profile, PROFILE_CONSTRAINTS["moderate"])

    # compute reserve
    if monthly_expenses > 0:
        reserve_pct = min(round(monthly_expenses * reserve_months / total_value, 2), 0.55)
    else:
        reserve_pct = constraints["min_liquid_pct"]

    invest_pct = round(1.0 - reserve_pct, 2)

    portfolio = Portfolio(
        name=f"Carteira {profile.capitalize()}",
        total_value=total_value,
        monthly_expenses=monthly_expenses,
        reserve_months=reserve_months,
        rebalancing_months=3,
        description="heuristic fallback (insufficient data for markowitz)",
    )

    # allocate reserve
    selic_pct = round(reserve_pct * 0.55, 2)
    cdb_pct = round(reserve_pct - selic_pct, 2)

    if "tesouro_selic" in catalog and selic_pct > 0:
        portfolio.add_allocation(catalog["tesouro_selic"], selic_pct)
    if "cdb_liquidez" in catalog and cdb_pct > 0:
        portfolio.add_allocation(catalog["cdb_liquidez"], cdb_pct)

    # allocate investment portion based on profile
    if profile == "conservative":
        allocs = [
            ("tesouro_ipca_juros", 0.30),
            ("lci_lca", 0.25),
            ("tesouro_ipca", 0.15),
            ("cdb_prefixado", 0.20),
            ("debenture_incentivada", 0.10),
        ]
    elif profile == "aggressive":
        allocs = [
            ("tesouro_ipca", 0.15),
            ("lci_lca", 0.10),
            ("debenture_incentivada", 0.10),
            ("fii", 0.15),
            ("etf_ibov", 0.20),
            ("etf_sp500", 0.15),
            ("etf_small_caps", 0.10),
            ("cripto_btc", 0.05),
        ]
    else:  # moderate
        allocs = [
            ("tesouro_ipca_juros", 0.15),
            ("lci_lca", 0.20),
            ("tesouro_ipca", 0.15),
            ("debenture_incentivada", 0.10),
            ("fii", 0.15),
            ("etf_ibov", 0.15),
            ("etf_sp500", 0.10),
        ]

    for key, pct in allocs:
        if key in catalog:
            actual_pct = round(invest_pct * pct, 4)
            if actual_pct > 0:
                portfolio.add_allocation(catalog[key], actual_pct)

    # fix rounding
    gap = round(1.0 - portfolio.total_allocation_pct, 4)
    if gap > 0.001 and "tesouro_selic" in catalog:
        portfolio.add_allocation(catalog["tesouro_selic"], gap)

    return portfolio


def compute_forward_projections(
    macro: MacroScenario,
    portfolio: Portfolio,
    years: int = 5,
) -> List[Dict]:
    """
    compute year-by-year forward projections using bcb focus trajectory.

    for each year, calculates:
    - gross portfolio return
    - net return (after ir regressivo + custody)
    - real return (net minus inflation)
    - macro indicators (selic, cdi, ipca for that year)
    """
    selic_path = macro.build_selic_path(years * 12)
    ipca_path = macro.build_ipca_path(years * 12)
    cdi_path = macro.build_cdi_path(years * 12)

    projections = []
    cumulative_value = portfolio.total_value

    for year in range(years):
        start_m = year * 12
        end_m = min(start_m + 12, len(selic_path))
        selic_avg = float(np.mean(selic_path[start_m:end_m]))
        cdi_avg = float(np.mean(cdi_path[start_m:end_m]))
        ipca_avg = float(np.mean(ipca_path[start_m:end_m]))

        # ir bracket for this year
        holding_months = (year + 1) * 12
        gross_return = portfolio.weighted_expected_annual_return
        net_return = portfolio.expected_net_annual_return(holding_months)
        real_return = net_return - ipca_avg

        # compound value
        cumulative_value *= (1 + net_return)

        projections.append({
            "year": year + 1,
            "selic_pct": round(selic_avg * 100, 2),
            "cdi_pct": round(cdi_avg * 100, 2),
            "ipca_pct": round(ipca_avg * 100, 2),
            "gross_return_pct": round(gross_return * 100, 2),
            "net_return_pct": round(net_return * 100, 2),
            "real_return_pct": round(real_return * 100, 2),
            "projected_value": round(cumulative_value, 2),
            "projected_monthly_income": round(
                cumulative_value * ((1 + net_return) ** (1/12) - 1), 2
            ),
        })

    return projections
