from dataclasses import dataclass, field
from typing import Dict
import numpy as np


@dataclass
class SimulationResult:
    """
    Value object containing the results of a simulation.
    """

    scenario_name: str
    simulation_type: str
    num_simulations: int
    horizon_months: int
    paths: np.ndarray
    monthly_returns: np.ndarray
    percentiles: Dict[str, float] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)

    def compute_percentiles(self) -> Dict[str, float]:
        """compute percentiles of the final portfolio value."""
        final_values = self.paths[:, -1]
        self.percentiles = {
            "p5": float(np.percentile(final_values, 5)),
            "p10": float(np.percentile(final_values, 10)),
            "p25": float(np.percentile(final_values, 25)),
            "p50": float(np.percentile(final_values, 50)),
            "p75": float(np.percentile(final_values, 75)),
            "p90": float(np.percentile(final_values, 90)),
            "p95": float(np.percentile(final_values, 95)),
            "mean": float(np.mean(final_values)),
            "std": float(np.std(final_values)),
            "min": float(np.min(final_values)),
            "max": float(np.max(final_values)),
        }
        return self.percentiles

    def compute_monthly_income_stats(self, initial_value: float) -> Dict[str, float]:
        """compute statistics about monthly income across simulations."""
        # average monthly return across all paths
        avg_monthly_returns = np.mean(self.monthly_returns, axis=1)
        monthly_incomes = avg_monthly_returns * initial_value

        return {
            "mean_monthly_income": float(np.mean(monthly_incomes)),
            "median_monthly_income": float(np.median(monthly_incomes)),
            "p5_monthly_income": float(np.percentile(monthly_incomes, 5)),
            "p95_monthly_income": float(np.percentile(monthly_incomes, 95)),
            "std_monthly_income": float(np.std(monthly_incomes)),
        }

    def probability_above_target(self, target_value: float) -> float:
        """probability that the final value exceeds a target."""
        final_values = self.paths[:, -1]
        return float(np.mean(final_values >= target_value))

    def probability_of_loss(self, initial_value: float) -> float:
        """probability of ending with less than the initial investment."""
        final_values = self.paths[:, -1]
        return float(np.mean(final_values < initial_value))

    def to_dict(self) -> Dict:
        """convert to a serializable dictionary (without numpy arrays)."""
        return {
            "scenario_name": self.scenario_name,
            "simulation_type": self.simulation_type,
            "num_simulations": self.num_simulations,
            "horizon_months": self.horizon_months,
            "percentiles": self.percentiles,
            "metrics": self.metrics,
        }
