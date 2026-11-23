from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

class LiquidityInput(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol")

class LiquidityTool(BaseTool):
    name: str = "Liquidity & Smart Money Analysis Tool"
    description: str = "Analyzes institutional flows, volume impact, and market regime to detect 'Smart Money' footprints."
    args_schema: Type[BaseModel] = LiquidityInput

    def _run(self, ticker: str) -> str:
        try:
            from utils.finance_data import fetch_price_history
            import pandas as pd
            import numpy as np
            
            # 1. Fetch Price & Volume Data
            df = fetch_price_history(ticker, period="3mo")
            if df.empty or len(df) < 20:
                return f"Insufficient data for liquidity analysis of {ticker}."
            
            # Note: fetch_price_history usually returns 'close' only. 
            # We need Volume. We will use yfinance directly for this advanced analysis.
            import yfinance as yf
            
            is_korea = ".KS" in ticker or ".KQ" in ticker or (len(ticker) == 6 and ticker.isdigit())
            yf_ticker = ticker
            if is_korea and not ticker.endswith(".KS") and not ticker.endswith(".KQ"):
                yf_ticker = f"{ticker}.KS"
                
            df_full = yf.download(yf_ticker, period="3mo", progress=False)
            if df_full.empty:
                 return f"Failed to fetch volume data for {ticker}."
            
             # Flatten MultiIndex if necessary
            if isinstance(df_full.columns, pd.MultiIndex):
                df_full.columns = df_full.columns.get_level_values(0)
            
            # Rename columns to standard lowercase
            df_full.columns = [c.lower() for c in df_full.columns]
            
            close = df_full['close']
            volume = df_full['volume']
            
            # =========================================================
            # CONCEPT 1: Relative Volume (RVR) - Liquidity Spike Detection
            # =========================================================
            avg_vol_20 = volume.rolling(20).mean().iloc[-1]
            cur_vol = volume.iloc[-1]
            
            rvr = 0.0
            if avg_vol_20 > 0:
                rvr = cur_vol / avg_vol_20
            
            vol_signal = "Normal"
            if rvr > 2.5: vol_signal = "Massive Spike (Institutional Footprint Possible)"
            elif rvr > 1.5: vol_signal = "High Volume"
            elif rvr < 0.5: vol_signal = "Dry Liquidity"
            
            # =========================================================
            # CONCEPT 2: Volume-Price Trend (Accumulation vs Distribution)
            # =========================================================
            # Simplest proxy for Institutional Activity: OBV Divergence or Price-Vol Correlation
            # If Price Up + Vol Up -> Accumulation
            # If Price Down + Vol Up -> Distribution
            
            recent_corr = close.tail(10).corr(volume.tail(10))
            
            flow_status = "Neutral"
            if recent_corr > 0.5 and close.iloc[-1] > close.iloc[-10]:
                flow_status = "Accumulation (Price & Vol Up)"
            elif recent_corr > 0.5 and close.iloc[-1] < close.iloc[-10]:
                flow_status = "Distribution (Selling on Volume)"
            elif recent_corr < -0.5:
                 flow_status = "Divergence (Watch out)"

            # =========================================================
            # CONCEPT 3: Institutional Tracking (Korea Specific)
            # =========================================================
            inst_msg = "N/A (US Stock)"
            if is_korea:
                # Mock logic for PyKRX to avoid dependency issues in this environment
                # In real prod, use pykrx.stock.get_market_trading_value_by_date
                inst_msg = "Requires PyKRX integration for precise data."
                
                # Try to infer from simplistic heuristic: 
                # Gap Up opening often implies institutional overnight orders
                try:
                    open_price = df_full['open'].iloc[-1]
                    prev_close = df_full['close'].iloc[-2]
                    gap = (open_price / prev_close - 1) * 100
                    if gap > 1.0:
                        inst_msg = "Gap Up (>1%) - Likely Institutional Interest"
                except:
                    pass

            # =========================================================
            # CONCEPT 4: Regime (Volatility)
            # =========================================================
            # Using ATR (Average True Range) as volatility proxy
            high = df_full['high']
            low = df_full['low']
            tr = np.maximum(high - low, np.maximum(abs(high - close.shift(1)), abs(low - close.shift(1))))
            atr = tr.rolling(14).mean().iloc[-1]
            atr_pct = (atr / close.iloc[-1]) * 100
            
            regime = "Stable"
            if atr_pct > 3.0: regime = "High Volatility (Risk-Off)"
            elif atr_pct < 1.0: regime = "Low Volatility (Risk-On)"

            # Construct Report
            report = f"""[Liquidity & Smart Money Analysis]
Ticker: {ticker}
Regime: {regime} (ATR: {atr_pct:.2f}%)

1. Flow Analysis:
- Volume Ratio (RVR): {rvr:.2f}x ({vol_signal})
- Flow Status: {flow_status} (Corr: {recent_corr:.2f})

2. Institutional Footprint:
- {inst_msg}

3. Smart Money Conclusion:
"""
            if rvr > 1.5 and "Accumulation" in flow_status:
                report += "-> POSITIVE: Distinct signs of institutional accumulation detected."
            elif rvr > 1.5 and "Distribution" in flow_status:
                report += "-> NEGATIVE: Heavy selling pressure detected (Distribution)."
            else:
                report += "-> NEUTRAL: No significant smart money anomalies."
                
            return report

        except Exception as e:
             return f"Error in Liquidity Tool: {str(e)}"

# Instantiate
liquidity_tool = LiquidityTool()
