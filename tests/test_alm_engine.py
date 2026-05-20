"""
unit tests for the alm engine components.
"""
import sys
from pathlib import Path

import pytest
import numpy as np

# ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.domain.entities.alm_entities import (
    CashFlowYear, AssetIndex, AssetSegment, RegulatoryArticle,
    ProjectionModel, PortfolioHolding, CurrentPortfolio,
    OptimizedPortfolio, SolvencyResult, BondAllocation,
)
from app.application.services.actuarial_flow_parser import (
    parse_cadprev_csv, get_flow_summary, get_deficit_years,
    _parse_br_number,
)
from app.application.services.alm_engine import (
    calculate_npv, calculate_required_return,
    calculate_npv_deficit_flows, project_patrimony,
    match_bonds_to_liabilities, generate_return_scenarios,
    simulate_solvency, load_alm_config,
    build_portfolio_from_config, build_indices_from_config,
    ALMEngine,
)


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_cashflows():
    """create minimal cashflow data for testing."""
    flows = []
    for i in range(30):
        year = 2026 + i
        # revenues decrease, expenditures increase over time
        revenues = max(0, 30_000_000 - i * 500_000)
        expenditures = 18_000_000 + i * 400_000
        flows.append(CashFlowYear(
            instant=i + 1,
            year=year,
            discount_rate=5.69,
            discount_factor=1 / (1.0569 ** i),
            contribution_base=5_000_000,
            total_revenues=revenues,
            total_expenditures=expenditures,
            financial_result=revenues - expenditures,
            accumulated_balance_pv=0.0,
            expected_return_pct=5.0,
            asset_return=0.0,
            guaranteed_resources=0.0,
        ))
    return flows


@pytest.fixture
def config_path():
    """path to the ipsemb config file."""
    return Path(__file__).resolve().parent.parent / "app" / "alm" / "config" / "ipsemb_2026.json"


@pytest.fixture
def csv_path():
    """path to the cadprev csv file."""
    return Path(__file__).resolve().parent.parent / "avaliacao atuarial" / "2026" / "2026_FLX_CIVIL_PREV_GA_01612525000140.csv"


# ---------------------------------------------------------------------------
# brazilian number parsing
# ---------------------------------------------------------------------------

class TestBRNumberParsing:
    def test_normal_number(self):
        assert _parse_br_number("1.234,56") == 1234.56

    def test_large_number(self):
        assert _parse_br_number("178.641.337,16") == 178641337.16

    def test_negative(self):
        assert _parse_br_number("-50.374.444,73") == -50374444.73

    def test_empty_string(self):
        assert _parse_br_number("") == 0.0

    def test_integer(self):
        assert _parse_br_number("2026") == 2026.0


# ---------------------------------------------------------------------------
# cadprev csv parser
# ---------------------------------------------------------------------------

class TestCadprevParser:
    def test_parse_csv(self, csv_path):
        if not csv_path.exists():
            pytest.skip("csv file not available")
        cashflows, meta = parse_cadprev_csv(csv_path)

        assert len(cashflows) > 100
        assert cashflows[0].year == 2026
        assert meta["actuarial_rate"] == 5.69 or meta["actuarial_rate"] == 5.0

    def test_flow_summary(self, csv_path):
        if not csv_path.exists():
            pytest.skip("csv file not available")
        cashflows, _ = parse_cadprev_csv(csv_path)
        summary = get_flow_summary(cashflows)

        assert summary["n_years"] == len(cashflows)
        assert summary["first_year"] == 2026
        assert summary["n_deficit_years"] > 0

    def test_deficit_years(self, csv_path):
        if not csv_path.exists():
            pytest.skip("csv file not available")
        cashflows, _ = parse_cadprev_csv(csv_path)
        deficits = get_deficit_years(cashflows)

        assert len(deficits) > 0
        for cf in deficits:
            assert cf.net_flow < 0


# ---------------------------------------------------------------------------
# npv and required return
# ---------------------------------------------------------------------------

class TestNPVCalculations:
    def test_npv_positive_return(self, sample_cashflows):
        result = calculate_npv(sample_cashflows, 0.10, 180_000_000)
        # with 10% return, should remain solvent
        assert result > 0

    def test_npv_zero_return(self, sample_cashflows):
        result = calculate_npv(sample_cashflows, 0.0, 180_000_000)
        # with 0% return, will eventually go negative
        assert result < 180_000_000

    def test_required_return_returns_value(self, sample_cashflows):
        rate = calculate_required_return(sample_cashflows, 180_000_000)
        # should return a positive rate within search bounds
        assert 0.0 <= rate <= 0.30

    def test_required_return_with_real_data(self, csv_path):
        """test with real cadprev data where we know the result should be ~5% real."""
        if not csv_path.exists():
            pytest.skip("csv file not available")
        cashflows, _ = parse_cadprev_csv(csv_path)
        rate = calculate_required_return(cashflows, 188_762_996.05)
        # ipsemb 2026: should be between 3% and 15%
        assert 0.03 < rate < 0.15


# ---------------------------------------------------------------------------
# patrimony projection
# ---------------------------------------------------------------------------

class TestPatrimonyProjection:
    def test_projection_length(self, sample_cashflows):
        proj = project_patrimony(sample_cashflows, 180_000_000, 0.08)
        assert len(proj) == len(sample_cashflows)

    def test_projection_has_required_keys(self, sample_cashflows):
        proj = project_patrimony(sample_cashflows, 180_000_000, 0.08)
        required_keys = [
            "year", "revenues", "expenditures",
            "flow_without_investments", "investment_result",
            "annual_flow", "projected_patrimony",
        ]
        for key in required_keys:
            assert key in proj[0]


# ---------------------------------------------------------------------------
# bond matching
# ---------------------------------------------------------------------------

class TestBondMatching:
    def test_bond_matching_returns_allocations(self, sample_cashflows):
        allocs = match_bonds_to_liabilities(
            sample_cashflows, 5.69, 0.30, 180_000_000
        )
        assert len(allocs) > 0

    def test_bond_weights_sum_to_one(self, sample_cashflows):
        allocs = match_bonds_to_liabilities(
            sample_cashflows, 5.69, 0.30, 180_000_000
        )
        if allocs:
            total = sum(a.weight_portfolio for a in allocs)
            assert abs(total - 1.0) < 0.01


# ---------------------------------------------------------------------------
# monte carlo
# ---------------------------------------------------------------------------

class TestMonteCarlo:
    def test_scenario_shape(self):
        scenarios = generate_return_scenarios(0.08, 0.05, 100, 30)
        assert scenarios.shape == (100, 30)

    def test_deterministic_when_zero_vol(self):
        scenarios = generate_return_scenarios(0.08, 0.0, 10, 5)
        assert np.allclose(scenarios, 0.08)

    def test_mean_converges(self):
        scenarios = generate_return_scenarios(0.08, 0.05, 10000, 1)
        mean = np.mean(scenarios)
        # gbm mean should be close to exp(mu) - 1
        expected = np.exp(0.08) - 1
        assert abs(mean - expected) < 0.01

    def test_solvency_simulation(self, sample_cashflows):
        returns = generate_return_scenarios(0.08, 0.05, 50, 30)
        inflation = generate_return_scenarios(0.04, 0.02, 50, 30, seed=99)

        result = simulate_solvency(
            sample_cashflows, 180_000_000,
            returns, inflation, 5.69,
        )
        assert "pct_solvent" in result
        assert "mean_funding_ratio" in result
        assert 0 <= result["pct_solvent"] <= 100


# ---------------------------------------------------------------------------
# config loading
# ---------------------------------------------------------------------------

class TestConfigLoading:
    def test_load_config(self, config_path):
        if not config_path.exists():
            pytest.skip("config file not available")
        config = load_alm_config(config_path)
        assert config["rpps_name"] == "IPSEMB - Instituto de Previdência Social dos Servidores Municipais de Buriticupu"
        assert config["patrimony"] > 0

    def test_build_portfolio(self, config_path):
        if not config_path.exists():
            pytest.skip("config file not available")
        config = load_alm_config(config_path)
        portfolio = build_portfolio_from_config(config)
        assert len(portfolio.holdings) == 16
        assert portfolio.total_patrimony > 0

    def test_build_indices(self, config_path):
        if not config_path.exists():
            pytest.skip("config file not available")
        config = load_alm_config(config_path)
        indices = build_indices_from_config(config)
        assert len(indices) == 18


# ---------------------------------------------------------------------------
# full engine integration
# ---------------------------------------------------------------------------

class TestALMEngineIntegration:
    def test_full_run(self, config_path, csv_path):
        if not config_path.exists() or not csv_path.exists():
            pytest.skip("config or csv file not available")

        engine = ALMEngine(config_path)
        engine.load_cashflows(csv_path)
        result = engine.run(n_scenarios=50, horizon_years=20)

        assert result.rpps_name is not None
        assert result.required_return > 0
        assert result.npv_deficit_flows < 0
        assert len(result.solvency_results) > 0
        assert len(result.bond_allocations) >= 0
