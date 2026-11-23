from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

class ValuationInput(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol")

class ValuationTool(BaseTool):
    name: str = "Valuation Analysis Tool"
    description: str = "Estimates the Fair Value of a stock using Analyst Consensus, PEG, and Fundamental models to propose a Target Price."
    args_schema: Type[BaseModel] = ValuationInput

    def _run(self, ticker: str) -> str:
        try:
            from utils.finance_data import fetch_fundamentals, fetch_price_history
            import pandas as pd
            
            # 1. Fetch data
            fund = fetch_fundamentals(ticker)
            df = fetch_price_history(ticker, period="1d")
            
            # Use current price from fund (real-time) or fallback to recent history
            current_price = fund.get('current_price')
            if (not current_price or current_price == 0) and not df.empty:
                current_price = float(df['close'].iloc[-1])
                
            if not current_price or current_price == 0:
                return f"Insufficient price data for valuation of {ticker}."
            
            pe = fund.get('pe')
            eps = fund.get('eps')
            bps = fund.get('bps')
            pb = fund.get('pb')
            peg = fund.get('peg_ratio')
            target_mean = fund.get('target_mean_price')
            growth = fund.get('earnings_growth') or fund.get('revenue_growth_yoy')
            
            valid_models = []
            estimates = []
            
            # --- Model 1: Analyst Consensus (High Reliability) ---
            if target_mean and target_mean > 0:
                estimates.append(target_mean)
                valid_models.append(f"Analyst Consensus: ${target_mean:.2f}")

            # --- Model 2: PEG Ratio Implied Value (Growth Adjusted) ---
            # Fair Value = CurrentPrice * (FairPEG / CurrentPEG)
            # We assume Fair PEG is 1.5 (Conservative) to 2.0 (High Growth/Moat)
            # If missing, fallback to Growth-based PE calculation
            if peg and peg > 0:
                # Adjust Fair PEG based on size/moat (Simple heuristic: 2.0 for everything for now to be generous to Tech)
                fair_peg = 2.0 
                # Avoid extreme multipliers
                if peg < 0.5: # Suspect data
                     pass 
                else:
                    fair_value_peg = current_price * (fair_peg / peg)
                    # Cap extreme upside/downside from single model
                    if fair_value_peg > current_price * 1.5: fair_value_peg = current_price * 1.5
                    if fair_value_peg < current_price * 0.5: fair_value_peg = current_price * 0.5
                    
                    estimates.append(fair_value_peg)
                    valid_models.append(f"PEG Model (Fair PEG {fair_peg}): ${fair_value_peg:.2f}")
            
            elif pe and growth and growth > 0:
                # Fallback: Fair PE = GrowthRate * PEG_Factor
                # Growth is usually 0.XX (e.g. 0.15) -> 15
                g_val = growth * 100
                fair_pe = g_val * 1.5
                fair_pe = min(fair_pe, 40) # Cap Fair PE
                if eps and eps > 0:
                    fv = fair_pe * eps
                    estimates.append(fv)
                    valid_models.append(f"Growth Model (Implied PE {fair_pe:.1f}x): ${fv:.2f}")

            # --- Model 3: Graham Number (Value Oriented) ---
            # Only apply if P/B is reasonable (< 5.0), otherwise it punishes Tech too much
            # Or if it's a known value stock. For general purpose, we restrict it.
            if eps and bps and eps > 0 and bps > 0:
                graham = (22.5 * eps * bps) ** 0.5
                if pb and pb > 5.0:
                    valid_models.append(f"Graham Number: ${graham:.2f} (Excluded: High P/B {pb:.1f})")
                else:
                    estimates.append(graham)
                    valid_models.append(f"Graham Number: ${graham:.2f}")

            # --- Consensus Logic ---
            if not estimates:
                 # If no models worked, fallback to current price or P/E based simple estimation
                 if pe and eps:
                     # Assume historical avg PE of 20
                     hist_pe_val = 20 * eps
                     estimates.append(hist_pe_val)
                     valid_models.append(f"Historical PE Proxy (20x): ${hist_pe_val:.2f}")
                 else:
                     return f"Valuation inconclusive for {ticker} (Missing key metrics). Current Price: ${current_price:.2f}"

            avg_fair_value = sum(estimates) / len(estimates)
            upside = (avg_fair_value / current_price - 1) * 100
            
            # Rating Logic
            rating = "HOLD"
            if upside > 15: rating = "BUY"
            elif upside < -10: rating = "SELL"
            
            result = f"""[Valuation Analysis Report]
Ticker: {ticker}
Current Price: ${current_price:.2f}

1. Valuation Models:
{chr(10).join(['- ' + m for m in valid_models])}

2. Fair Value Estimate:
- Target Price: ${avg_fair_value:.2f}
- Upside Potential: {upside:+.1f}%

3. Investment Rating: {rating}
"""
            return result

        except Exception as e:
            return f"Error in Valuation Tool: {str(e)}"

# Instantiate
valuation_tool = ValuationTool()
