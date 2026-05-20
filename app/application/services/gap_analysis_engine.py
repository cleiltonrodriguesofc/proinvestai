"""
gap analysis engine — compares current vs ideal portfolio.

updated to use the new allocation model (alloc.percentage, alloc.asset.asset_class).
"""

import logging
from typing import Dict
from dataclasses import dataclass
from ...domain.entities.portfolio import Portfolio

logger = logging.getLogger(__name__)


@dataclass
class GapResult:
    current_allocation: Dict[str, float]
    ideal_allocation: Dict[str, float]
    deviations: Dict[str, float]
    total_misallocated_capital: float
    potential_gain_lost: float


class GapAnalysisEngine:
    """
    compares the user's current real portfolio against the idealized
    markowitz portfolio and identifies gaps and opportunity costs.
    """
    
    def compare(self, current_portfolio: Portfolio, ideal_portfolio: Portfolio, initial_amount: float) -> GapResult:
        # calculate current weights by asset class
        current_weights = {}
        for alloc in current_portfolio.allocations:
            a_class = alloc.asset.asset_class.value
            current_weights[a_class] = current_weights.get(a_class, 0.0) + float(alloc.percentage)
            
        # calculate ideal weights by asset class
        ideal_weights = {}
        for alloc in ideal_portfolio.allocations:
            a_class = alloc.asset.asset_class.value
            ideal_weights[a_class] = ideal_weights.get(a_class, 0.0) + float(alloc.percentage)
            
        # find all unique asset classes present in either portfolio
        all_classes = set(current_weights.keys()).union(set(ideal_weights.keys()))
        
        deviations = {}
        misallocated_pct = 0.0
        
        for a_class in all_classes:
            curr = current_weights.get(a_class, 0.0)
            ideal = ideal_weights.get(a_class, 0.0)
            diff = curr - ideal
            deviations[a_class] = diff
            misallocated_pct += abs(diff)
            
        misallocated_pct = misallocated_pct / 2.0
        misallocated_capital = initial_amount * misallocated_pct
        
        # estimate opportunity cost using the new portfolio properties
        curr_return = current_portfolio.weighted_expected_annual_return
        ideal_return = ideal_portfolio.weighted_expected_annual_return
        
        if ideal_return > curr_return:
            potential_gain_lost = initial_amount * (ideal_return - curr_return)
        else:
            potential_gain_lost = misallocated_capital * 0.05
            
        return GapResult(
            current_allocation=current_weights,
            ideal_allocation=ideal_weights,
            deviations=deviations,
            total_misallocated_capital=misallocated_capital,
            potential_gain_lost=potential_gain_lost
        )
