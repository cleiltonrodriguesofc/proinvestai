import logging
from typing import Dict, Any
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
    Service responsible for comparing the user's current real portfolio
    against the idealized Markowitz portfolio and identifying gaps and opportunity costs.
    """
    
    def compare(self, current_portfolio: Portfolio, ideal_portfolio: Portfolio, initial_amount: float) -> GapResult:
        # Calculate current weights
        current_weights = {}
        for alloc in current_portfolio.allocations:
            a_class = alloc.asset.asset_class.value
            current_weights[a_class] = current_weights.get(a_class, 0.0) + float(alloc.weight)
            
        # Calculate ideal weights
        ideal_weights = {}
        for alloc in ideal_portfolio.allocations:
            a_class = alloc.asset.asset_class.value
            ideal_weights[a_class] = ideal_weights.get(a_class, 0.0) + float(alloc.weight)
            
        # Find all unique asset classes present in either portfolio
        all_classes = set(current_weights.keys()).union(set(ideal_weights.keys()))
        
        deviations = {}
        misallocated_pct = 0.0
        
        for a_class in all_classes:
            curr = current_weights.get(a_class, 0.0)
            ideal = ideal_weights.get(a_class, 0.0)
            diff = curr - ideal
            deviations[a_class] = diff
            
            # We only sum absolute deviations and divide by 2 to get the total misallocated %
            # (since every +X% over-allocation corresponds to a -X% under-allocation elsewhere)
            misallocated_pct += abs(diff)
            
        misallocated_pct = misallocated_pct / 2.0
        misallocated_capital = initial_amount * misallocated_pct
        
        # Estimate opportunity cost: assuming ideal portfolio yields higher return.
        # This is simplified; ideally we'd compare the expected_return directly.
        curr_return = float(current_portfolio.expected_return) if current_portfolio.expected_return else 0.0
        ideal_return = float(ideal_portfolio.expected_return) if ideal_portfolio.expected_return else 0.0
        
        # If ideal return is higher, the lost gain is the difference applied to the full capital.
        # If we only want to apply it to misallocated capital, we can adjust logic.
        # Let's apply difference to total capital, or just use misallocated_capital * 0.05 as fallback.
        if ideal_return > curr_return:
            potential_gain_lost = initial_amount * (ideal_return - curr_return)
        else:
            # Fallback heuristic
            potential_gain_lost = misallocated_capital * 0.05
            
        return GapResult(
            current_allocation=current_weights,
            ideal_allocation=ideal_weights,
            deviations=deviations,
            total_misallocated_capital=misallocated_capital,
            potential_gain_lost=potential_gain_lost
        )
