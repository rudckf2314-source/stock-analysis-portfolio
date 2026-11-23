"""
CVaR (Conditional Value at Risk) Constraint Optimization

CVaR는 꼬리위험(Tail Risk)을 측정하고 제한하는 리스크 지표입니다.
VaR를 초과하는 손실의 평균값으로, 극단적 손실 시나리오를 방어합니다.

CVaR_α(X) = E[X | X >= VaR_α(X)]

예: CVaR_95 = 0.10 의미
→ 최악의 5% 시나리오에서 평균 손실이 10% 이하로 제한

Reference:
- Rockafellar, R.T., & Uryasev, S. (2000). "Optimization of conditional value-at-risk"
"""

import numpy as np
import pandas as pd
import cvxpy as cp
from typing import Dict, Optional


class CVaRConstraintOptimizer:
    """
    CVaR 제약을 적용한 포트폴리오 최적화
    """
    
    def __init__(
        self,
        returns: pd.DataFrame,
        cvar_limit: float = 0.10,
        confidence_level: float = 0.95
    ):
        """
        Initialize CVaR constraint optimizer.
        
        Args:
            returns: DataFrame of historical returns (dates × assets)
            cvar_limit: Maximum allowed CVaR (예: 0.10 = 10%)
            confidence_level: Confidence level for CVaR (예: 0.95 = 95%)
        """
        self.returns = returns
        self.assets = returns.columns.tolist()
        self.n_assets = len(self.assets)
        self.n_scenarios = len(returns)
        
        self.cvar_limit = cvar_limit
        self.alpha = confidence_level
    
    def optimize_with_cvar(
        self,
        initial_weights: Optional[Dict[str, float]] = None,
        target_return: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Optimize portfolio with CVaR constraint.
        
        Args:
            initial_weights: Initial weights from HRP (optional)
            target_return: Target expected return (optional)
            
        Returns:
            Dictionary of {asset: weight} satisfying CVaR constraint
        """
        # Decision variables
        w = cp.Variable(self.n_assets)  # Portfolio weights
        
        # Objective: Minimize deviation from initial weights (if provided)
        # or minimize variance
        if initial_weights is not None:
            w_init = np.array([initial_weights.get(asset, 0) for asset in self.assets])
            objective = cp.Minimize(cp.sum_squares(w - w_init))
        else:
            # Minimize variance
            cov_matrix = self.returns.cov().values
            objective = cp.Minimize(cp.quad_form(w, cov_matrix))
        
        # Constraints
        constraints = [
            cp.sum(w) == 1,  # Weights sum to 1
            w >= 0,  # No short selling
            w <= 0.20,  # Single asset limit (20%)
        ]
        
        # CVaR constraint
        cvar_constraint = self._create_cvar_constraint(w)
        constraints.append(cvar_constraint)
        
        # Target return constraint (optional)
        if target_return is not None:
            mean_returns = self.returns.mean().values
            constraints.append(w @ mean_returns >= target_return)
        
        # Solve
        problem = cp.Problem(objective, constraints)
        
        try:
            problem.solve(solver=cp.ECOS)
            
            if problem.status not in ["optimal", "optimal_inaccurate"]:
                print(f"⚠️ CVaR Optimization failed: {problem.status}")
                # Fallback to equal weights
                return {asset: 1.0 / self.n_assets for asset in self.assets}
            
            # Extract weights
            weights_array = w.value
            weights = {
                asset: max(0, weight)  # Ensure non-negative
                for asset, weight in zip(self.assets, weights_array)
            }
            
            # Normalize
            total = sum(weights.values())
            if total > 0:
                weights = {k: v / total for k, v in weights.items()}
            
            return weights
            
        except Exception as e:
            print(f"❌ CVaR Optimization error: {e}")
            # Fallback
            if initial_weights:
                return initial_weights
            else:
                return {asset: 1.0 / self.n_assets for asset in self.assets}
    
    def _create_cvar_constraint(self, w: cp.Variable) -> cp.constraints.constraint.Constraint:
        """
        Create CVaR constraint using LP formulation.
        
        CVaR can be formulated as a linear program:
        CVaR_α(w) = min_t { t + (1/(1-α)) * E[max(0, -R*w - t)] }
        
        Returns:
            CVaR constraint
        """
        # Scenario returns (negative for losses)
        scenario_returns = -self.returns.values  # (n_scenarios × n_assets)
        
        # Auxiliary variable for VaR
        t = cp.Variable()
        
        # Auxiliary variables for excess losses
        u = cp.Variable(self.n_scenarios)
        
        # CVaR = t + (1/(1-α)) * mean(u)
        cvar = t + (1.0 / (1 - self.alpha)) * cp.sum(u) / self.n_scenarios
        
        # Constraints: u[i] >= max(0, -R[i]*w - t)
        for i in range(self.n_scenarios):
            # u[i] >= -R[i]*w - t
            # u[i] >= 0
            pass  # Handled below
        
        # Vectorized form
        constraints = [
            u >= 0,
            u >= scenario_returns @ w - t
        ]
        
        # Return CVaR constraint
        return cvar <= self.cvar_limit
    
    def calculate_cvar(self, weights: Dict[str, float]) -> float:
        """
        Calculate CVaR for a given portfolio.
        
        Args:
            weights: Portfolio weights
            
        Returns:
            CVaR value
        """
        # Convert weights to array
        w_array = np.array([weights.get(asset, 0) for asset in self.assets])
        
        # Calculate portfolio returns
        portfolio_returns = (self.returns.values @ w_array)
        
        # Calculate VaR (percentile)
        var = np.percentile(portfolio_returns, (1 - self.alpha) * 100)
        
        # CVaR = mean of returns below VaR
        tail_returns = portfolio_returns[portfolio_returns <= var]
        cvar = -np.mean(tail_returns)
        
        return cvar


# ============================================================
# Usage Helper Function
# ============================================================

def apply_cvar_constraint(
    hrp_weights: Dict[str, float],
    returns: pd.DataFrame,
    cvar_limit: float = 0.10
) -> Dict[str, float]:
    """
    Apply CVaR constraint to HRP weights.
    
    Args:
        hrp_weights: Initial weights from HRP
        returns: Historical returns
        cvar_limit: Maximum CVaR
        
    Returns:
        Adjusted weights satisfying CVaR constraint
    """
    optimizer = CVaRConstraintOptimizer(
        returns=returns,
        cvar_limit=cvar_limit,
        confidence_level=0.95
    )
    
    # Check if HRP weights already satisfy CVaR
    current_cvar = optimizer.calculate_cvar(hrp_weights)
    print(f"   HRP CVaR: {current_cvar:.4f}, Limit: {cvar_limit:.4f}")
    
    if current_cvar <= cvar_limit:
        print(f"   ✅ HRP weights already satisfy CVaR constraint")
        return hrp_weights
    
    # Optimize with CVaR constraint
    print(f"   🔧 Applying CVaR constraint optimization...")
    adjusted_weights = optimizer.optimize_with_cvar(
        initial_weights=hrp_weights
    )
    
    # Verify
    final_cvar = optimizer.calculate_cvar(adjusted_weights)
    print(f"   ✅ Adjusted CVaR: {final_cvar:.4f}")
    
    return adjusted_weights


# ============================================================
# Example Usage
# ============================================================

def example_cvar():
    """
    Example: CVaR constraint optimization
    """
    # Generate sample returns
    np.random.seed(42)
    assets = ['Asset_A', 'Asset_B', 'Asset_C']
    
    # Simulate returns with fat tails
    n_days = 252
    returns_data = {
        'Asset_A': np.random.normal(0.0005, 0.02, n_days),
        'Asset_B': np.random.normal(0.0007, 0.025, n_days),
        'Asset_C': np.random.normal(0.0006, 0.018, n_days),
    }
    returns = pd.DataFrame(returns_data)
    
    # Initial HRP weights
    hrp_weights = {
        'Asset_A': 0.35,
        'Asset_B': 0.40,
        'Asset_C': 0.25
    }
    
    # Apply CVaR constraint
    cvar_weights = apply_cvar_constraint(
        hrp_weights=hrp_weights,
        returns=returns,
        cvar_limit=0.08
    )
    
    print("\nCVaR-Constrained Weights:")
    for asset, weight in cvar_weights.items():
        print(f"  {asset}: {weight:.4f} ({weight*100:.2f}%)")
    
    return cvar_weights


if __name__ == "__main__":
    example_cvar()
