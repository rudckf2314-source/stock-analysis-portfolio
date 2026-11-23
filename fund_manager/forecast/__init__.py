"""
Fund Manager Forecast Module

성과 예측 알고리즘:
- Monte Carlo Simulation
- Goal Achievement Probability
"""

from .monte_carlo import MonteCarloForecaster, ForecastResult

__all__ = [
    'MonteCarloForecaster',
    'ForecastResult',
]
