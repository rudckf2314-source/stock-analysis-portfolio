"""
Monte Carlo Simulation for Portfolio Forecasting

포트폴리오의 미래 성과를 확률적으로 예측합니다.
- 분위수 기반 예측 (p10, p50, p90)
- 목표 달성 확률 계산
- 부족액 위험 (Shortfall Risk)
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple
from dataclasses import dataclass


@dataclass
class ForecastResult:
    """Monte Carlo 시뮬레이션 결과"""
    percentiles: Dict[str, float]  # p5, p10, p25, p50, p75, p90, p95
    expected_value: float
    std_dev: float
    goal_achievement_prob: float
    expected_shortfall_amount: float
    final_values: np.ndarray  # 전체 시뮬레이션 결과


class MonteCarloForecaster:
    """
    Monte Carlo 시뮬레이션 기반 포트폴리오 성과 예측
    """
    
    def __init__(
        self,
        returns: pd.DataFrame,
        weights: Dict[str, float],
        n_simulations: int = 10000
    ):
        """
        Initialize Monte Carlo forecaster.
        
        Args:
            returns: Historical returns DataFrame
            weights: Portfolio weights
            n_simulations: Number of Monte Carlo runs
        """
        self.returns = returns
        self.weights = weights
        self.n_simulations = n_simulations
        
        # Calculate portfolio statistics
        self.assets = returns.columns.tolist()
        w_array = np.array([weights.get(asset, 0) for asset in self.assets])
        
        self.mean_returns = returns.mean().values
        self.cov_matrix = returns.cov().values
        
        self.portfolio_mean = w_array @ self.mean_returns
        self.portfolio_std = np.sqrt(w_array @ self.cov_matrix @ w_array)
    
    def forecast(
        self,
        initial_capital: float,
        time_horizon_months: int,
        target_amount: Optional[float] = None
    ) -> ForecastResult:
        """
        Run Monte Carlo simulation.
        
        Args:
            initial_capital: Starting capital (원)
            time_horizon_months: Investment period (months)
            target_amount: Target amount (원) for goal probability
            
        Returns:
            ForecastResult
        """
        # Convert to daily simulation
        trading_days_per_month = 21
        n_days = time_horizon_months * trading_days_per_month
        
        # Annualized to daily
        daily_mean = self.portfolio_mean
        daily_std = self.portfolio_std / np.sqrt(252)
        
        # Monte Carlo simulations
        final_values = np.zeros(self.n_simulations)
        
        for i in range(self.n_simulations):
            # Generate random returns for each day
            daily_returns = np.random.normal(daily_mean, daily_std, n_days)
            
            # Compound to get final value
            cumulative_return = np.prod(1 + daily_returns)
            final_values[i] = initial_capital * cumulative_return
        
        # Calculate percentiles
        percentiles = {
            'p5': np.percentile(final_values, 5),
            'p10': np.percentile(final_values, 10),
            'p25': np.percentile(final_values, 25),
            'p50': np.percentile(final_values, 50),
            'p75': np.percentile(final_values, 75),
            'p90': np.percentile(final_values, 90),
            'p95': np.percentile(final_values, 95)
        }
        
        expected_value = np.mean(final_values)
        std_dev = np.std(final_values)
        
        # Goal achievement probability
        if target_amount is not None:
            goal_achievement_prob = np.mean(final_values >= target_amount)
            
            # Expected shortfall (부족액 평균)
            shortfalls = target_amount - final_values
            shortfalls = shortfalls[shortfalls > 0]  # Only positive shortfalls
            expected_shortfall = np.mean(shortfalls) if len(shortfalls) > 0 else 0.0
        else:
            goal_achievement_prob = 0.0
            expected_shortfall = 0.0
        
        return ForecastResult(
            percentiles=percentiles,
            expected_value=expected_value,
            std_dev=std_dev,
            goal_achievement_prob=goal_achievement_prob,
            expected_shortfall_amount=expected_shortfall,
            final_values=final_values
        )
    
    def calculate_return_distribution(
        self,
        time_horizon_months: int
    ) -> Dict[str, float]:
        """
        Calculate return distribution (as percentages).
        
        Returns:
            Dictionary with return percentiles
        """
        initial = 1.0
        forecast = self.forecast(
            initial_capital=initial,
            time_horizon_months=time_horizon_months
        )
        
        return_percentiles = {
            k: (v / initial - 1.0)
            for k, v in forecast.percentiles.items()
        }
        
        return_percentiles['expected'] = (forecast.expected_value / initial - 1.0)
        
        return return_percentiles


# ============================================================
# Example Usage
# ============================================================

def example_monte_carlo():
    """
    Example: Monte Carlo simulation
    """
    # Sample data
    np.random.seed(42)
    assets = ['Stock_A', 'Stock_B', 'Bond_ETF']
    
    n_days = 252
    returns_data = {
        'Stock_A': np.random.normal(0.0008, 0.02, n_days),
        'Stock_B': np.random.normal(0.0007, 0.018, n_days),
        'Bond_ETF': np.random.normal(0.0003, 0.005, n_days),
    }
    returns = pd.DataFrame(returns_data)
    
    # Portfolio weights
    weights = {
        'Stock_A': 0.40,
        'Stock_B': 0.35,
        'Bond_ETF': 0.25
    }
    
    # Forecast
    forecaster = MonteCarloForecaster(
        returns=returns,
        weights=weights,
        n_simulations=10000
    )
    
    result = forecaster.forecast(
        initial_capital=50_000_000,  # 5천만원
        time_horizon_months=60,  # 5년
        target_amount=75_000_000  # 목표 7천5백만원
    )
    
    print("Monte Carlo Forecast (5년, 5천만원 → 목표 7천5백만원):")
    print(f"\n  예상 최종 금액: {result.expected_value:,.0f}원")
    print(f"  표준편차: {result.std_dev:,.0f}원")
    print(f"\n  분위수:")
    for p, val in result.percentiles.items():
        print(f"    {p}: {val:,.0f}원")
    print(f"\n  목표 달성 확률: {result.goal_achievement_prob:.2%}")
    print(f"  예상 부족액 (실패 시): {result.expected_shortfall_amount:,.0f}원")
    
    # Return distribution
    ret_dist = forecaster.calculate_return_distribution(60)
    print(f"\n  수익률 분포:")
    for k, v in ret_dist.items():
        print(f"    {k}: {v:.2%}")
    
    return result


if __name__ == "__main__":
    example_monte_carlo()
