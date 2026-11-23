"""
Portfolio Generator - Integrated Engine

HRP + CVaR + Monte Carlo를 통합하여 3가지 포트폴리오를 생성합니다:
1. Base Case - 균형잡힌 포트폴리오
2. Upside-Seeking - 수익 극대화
3. Downside-Defensive - 손실 최소화
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
from dataclasses import dataclass

# Import our algorithms
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from construction.hrp import HRPOptimizer
from construction.cvar_constraint import CVaRConstraintOptimizer
from forecast.monte_carlo import MonteCarloForecaster


@dataclass
class IPS:
    """Investment Policy Statement"""
    risk_level: int  # 1-5
    target_vol: float  # 0.05-0.30
    max_drawdown_target: float  # 0.10-0.50
    cvar_limit_95: float  # 0.05-0.25
    equity_range: Tuple[float, float]  # (min, max)
    rebalance_band: float  # 0.03-0.10


@dataclass
class Portfolio:
    """Portfolio with all metadata"""
    name: str
    description: str
    holdings: Dict[str, float]  # {ticker: weight}
    expected_return: float
    expected_volatility: float
    estimated_cvar: float
    forecast_p10: float
    forecast_p50: float
    forecast_p90: float
    goal_achievement_prob: float


class PortfolioGenerator:
    """
    통합 포트폴리오 생성 엔진
    """
    
    def __init__(self, returns: pd.DataFrame, ips: IPS):
        """
        Initialize portfolio generator.
        
        Args:
            returns: Historical returns DataFrame
            ips: Investment Policy Statement
        """
        self.returns = returns
        self.ips = ips
        self.assets = returns.columns.tolist()
        
        # Calculate statistics
        self.mean_returns = returns.mean()
        self.cov_matrix = returns.cov()
    
    def generate_three_portfolios(
        self,
        initial_capital: float,
        time_horizon_months: int,
        target_amount: float = None
    ) -> Dict[str, Portfolio]:
        """
        Generate 3 portfolios: Base, Upside, Defensive.
        
        Args:
            initial_capital: Starting capital
            time_horizon_months: Investment period
            target_amount: Goal amount (optional)
            
        Returns:
            Dictionary of {name: Portfolio}
        """
        print("="*60)
        print("포트폴리오 생성 시작")
        print("="*60)
        
        # Step 1: Generate Base portfolio
        print("\n[1/3] Base Portfolio 생성...")
        base = self._generate_base_portfolio(
            initial_capital, time_horizon_months, target_amount
        )
        
        # Step 2: Generate Upside portfolio
        print("\n[2/3] Upside-Seeking Portfolio 생성...")
        upside = self._generate_upside_portfolio(
            initial_capital, time_horizon_months, target_amount
        )
        
        # Step 3: Generate Defensive portfolio
        print("\n[3/3] Downside-Defensive Portfolio 생성...")
        defensive = self._generate_defensive_portfolio(
            initial_capital, time_horizon_months, target_amount
        )
        
        print("\n" + "="*60)
        print("✅ 3가지 포트폴리오 생성 완료")
        print("="*60)
        
        return {
            "base": base,
            "upside": upside,
            "defensive": defensive
        }
    
    def _generate_base_portfolio(
        self,
        initial_capital: float,
        time_horizon_months: int,
        target_amount: float = None
    ) -> Portfolio:
        """Base Case: 균형잡힌 포트폴리오"""
        
        # Step 1: HRP
        print("   Step 1: HRP 최적화...")
        hrp = HRPOptimizer(self.returns)
        hrp_weights = hrp.optimize()
        
        # Step 2: CVaR Constraint
        print("   Step 2: CVaR 제약 적용...")
        cvar_opt = CVaRConstraintOptimizer(
            self.returns,
            cvar_limit=self.ips.cvar_limit_95
        )
        
        weights = cvar_opt.optimize_with_cvar(initial_weights=hrp_weights)
        
        # Step 3: Calculate metrics
        portfolio_stats = self._calculate_portfolio_stats(weights)
        
        # Step 4: Forecast
        print("   Step 3: Monte Carlo 예측...")
        forecast = self._run_forecast(
            weights, initial_capital, time_horizon_months, target_amount
        )
        
        return Portfolio(
            name="Base",
            description="설문 조건을 가장 충실히 반영한 균형 포트폴리오",
            holdings=weights,
            expected_return=portfolio_stats['return'],
            expected_volatility=portfolio_stats['volatility'],
            estimated_cvar=portfolio_stats['cvar'],
            forecast_p10=forecast['p10'],
            forecast_p50=forecast['p50'],
            forecast_p90=forecast['p90'],
            goal_achievement_prob=forecast['goal_prob']
        )
    
    def _generate_upside_portfolio(
        self,
        initial_capital: float,
        time_horizon_months: int,
        target_amount: float = None
    ) -> Portfolio:
        """Upside-Seeking: 수익 극대화"""
        
        # More aggressive: Increase equity range upper bound
        print("   전략: 주식 비중 상향 조정...")
        
        # Start with HRP
        hrp = HRPOptimizer(self.returns)
        hrp_weights = hrp.optimize()
        
        # Tilt towards higher expected returns
        # Increase weights of high-return assets
        adjusted_weights = self._tilt_to_returns(hrp_weights, factor=1.2)
        
        # Apply CVaR (use limit, not exceed)
        cvar_opt = CVaRConstraintOptimizer(
            self.returns,
            cvar_limit=self.ips.cvar_limit_95 * 1.0  # Use full limit
        )
        weights = cvar_opt.optimize_with_cvar(initial_weights=adjusted_weights)
        
        # Calculate & Forecast
        portfolio_stats = self._calculate_portfolio_stats(weights)
        forecast = self._run_forecast(
            weights, initial_capital, time_horizon_months, target_amount
        )
        
        return Portfolio(
            name="Upside-Seeking",
            description="동일 제약 하 기대수익 극대화",
            holdings=weights,
            expected_return=portfolio_stats['return'],
            expected_volatility=portfolio_stats['volatility'],
            estimated_cvar=portfolio_stats['cvar'],
            forecast_p10=forecast['p10'],
            forecast_p50=forecast['p50'],
            forecast_p90=forecast['p90'],
            goal_achievement_prob=forecast['goal_prob']
        )
    
    def _generate_defensive_portfolio(
        self,
        initial_capital: float,
        time_horizon_months: int,
        target_amount: float = None
    ) -> Portfolio:
        """Downside-Defensive: 손실 최소화"""
        
        print("   전략: 안정 자산 비중 확대...")
        
        # Start with HRP
        hrp = HRPOptimizer(self.returns)
        hrp_weights = hrp.optimize()
        
        # Tilt towards lower volatility assets
        adjusted_weights = self._tilt_to_stability(hrp_weights, factor=1.2)
        
        # Apply stricter CVaR
        cvar_opt = CVaRConstraintOptimizer(
            self.returns,
            cvar_limit=self.ips.cvar_limit_95 * 0.8  # Stricter limit
        )
        weights = cvar_opt.optimize_with_cvar(initial_weights=adjusted_weights)
        
        # Calculate & Forecast
        portfolio_stats = self._calculate_portfolio_stats(weights)
        forecast = self._run_forecast(
            weights, initial_capital, time_horizon_months, target_amount
        )
        
        return Portfolio(
            name="Downside-Defensive",
            description="손실 발생 확률/규모 최소화",
            holdings=weights,
            expected_return=portfolio_stats['return'],
            expected_volatility=portfolio_stats['volatility'],
            estimated_cvar=portfolio_stats['cvar'],
            forecast_p10=forecast['p10'],
            forecast_p50=forecast['p50'],
            forecast_p90=forecast['p90'],
            goal_achievement_prob=forecast['goal_prob']
        )
    
    def _tilt_to_returns(self, weights: Dict[str, float], factor: float) -> Dict[str, float]:
        """Tilt weights towards higher expected returns"""
        returns_array = np.array([self.mean_returns[asset] for asset in weights.keys()])
        weights_array = np.array(list(weights.values()))
        
        # Increase weights of high-return assets
        tilted = weights_array * (1 + factor * (returns_array - returns_array.mean()))
        tilted = np.maximum(tilted, 0)  # No negative
        tilted = tilted / tilted.sum()  # Normalize
        
        return {asset: weight for asset, weight in zip(weights.keys(), tilted)}
    
    def _tilt_to_stability(self, weights: Dict[str, float], factor: float) -> Dict[str, float]:
        """Tilt weights towards lower volatility assets"""
        # Calculate individual volatilities
        vols = self.returns.std()
        vols_array = np.array([vols[asset] for asset in weights.keys()])
        weights_array = np.array(list(weights.values()))
        
        # Increase weights of low-vol assets
        tilted = weights_array * (1 + factor * (vols_array.mean() - vols_array))
        tilted = np.maximum(tilted, 0)
        tilted = tilted / tilted.sum()
        
        return {asset: weight for asset, weight in zip(weights.keys(), tilted)}
    
    def _calculate_portfolio_stats(self, weights: Dict[str, float]) -> Dict[str, float]:
        """Calculate portfolio statistics"""
        w_array = np.array([weights.get(asset, 0) for asset in self.assets])
        
        # Expected return (annualized)
        exp_return = w_array @ self.mean_returns.values * 252
        
        # Volatility (annualized)
        volatility = np.sqrt(w_array @ self.cov_matrix.values @ w_array) * np.sqrt(252)
        
        # CVaR
        cvar_opt = CVaRConstraintOptimizer(self.returns, cvar_limit=1.0)
        cvar = cvar_opt.calculate_cvar(weights)
        
        return {
            'return': exp_return,
            'volatility': volatility,
            'cvar': cvar
        }
    
    def _run_forecast(
        self,
        weights: Dict[str, float],
        initial_capital: float,
        time_horizon_months: int,
        target_amount: float = None
    ) -> Dict[str, float]:
        """Run Monte Carlo forecast"""
        forecaster = MonteCarloForecaster(
            self.returns,
            weights,
            n_simulations=5000  # Reduced for speed
        )
        
        result = forecaster.forecast(
            initial_capital,
            time_horizon_months,
            target_amount
        )
        
        # Convert to returns
        init = initial_capital
        return {
            'p10': (result.percentiles['p10'] / init - 1.0),
            'p50': (result.percentiles['p50'] / init - 1.0),
            'p90': (result.percentiles['p90'] / init - 1.0),
            'goal_prob': result.goal_achievement_prob
        }


# ============================================================
# Example Usage
# ============================================================

def example_generator():
    """Example: Generate 3 portfolios"""
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
    
    # IPS
    ips = IPS(
        risk_level=3,
        target_vol=0.15,
        max_drawdown_target=0.20,
        cvar_limit_95=0.12,
        equity_range=(0.4, 0.8),
        rebalance_band=0.05
    )
    
    # Generate
    generator = PortfolioGenerator(returns, ips)
    portfolios = generator.generate_three_portfolios(
        initial_capital=50_000_000,
        time_horizon_months=60,
        target_amount=75_000_000
    )
    
    # Display
    for name, portfolio in portfolios.items():
        print(f"\n{portfolio.name}: {portfolio.description}")
        print(f"  기대수익률: {portfolio.expected_return:.2%}")
        print(f"  변동성: {portfolio.expected_volatility:.2%}")
        print(f"  CVaR 95%: {portfolio.estimated_cvar:.2%}")
        print(f"  예측 수익률 (p50): {portfolio.forecast_p50:.2%}")
        print(f"  목표 달성 확률: {portfolio.goal_achievement_prob:.2%}")
        print(f"  보유 종목:")
        for asset, weight in portfolio.holdings.items():
            print(f"    {asset}: {weight:.2%}")


if __name__ == "__main__":
    example_generator()
