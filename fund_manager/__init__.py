"""
FDGE Fund Manager - Core Algorithms

포트폴리오 생성 및 예측 알고리즘:
- HRP (Hierarchical Risk Parity)
- CVaR (Conditional Value at Risk) Constraint
- Monte Carlo Simulation
- Portfolio Generator

Usage:
    from fund_manager.construction import PortfolioGenerator, IPS
    from fund_manager.forecast import MonteCarloForecaster
    
    # Create IPS
    ips = IPS(
        risk_level=3,
        target_vol=0.15,
        max_drawdown_target=0.20,
        cvar_limit_95=0.12,
        equity_range=(0.4, 0.8),
        rebalance_band=0.05
    )
    
    # Generate portfolios
    generator = PortfolioGenerator(returns, ips)
    portfolios = generator.generate_three_portfolios(
        initial_capital=50_000_000,
        time_horizon_months=60,
        target_amount=75_000_000
    )
"""

__version__ = "1.0.0"
