"""
Fund Manager API Endpoints
- Robust Version: Handles data fetching failures gracefully
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import yfinance as yf
import pandas as pd
import numpy as np
import random

# Import models
from fund_manager.models import (
    SuitabilityRequest, SuitabilityResponse,
    UniverseRequest, UniverseResponse,
    ConstructionRequest, ConstructionResponse
)

# Create router
router = APIRouter(prefix="/api/fund", tags=["Fund Manager"])


@router.post("/suitability")
def analyze_suitability(request: SuitabilityRequest):
    """
    설문 응답 → 3축 프로파일 + IPS 생성
    
    Priority:
    1. Agent Analysis (agent_engine.fund_crew)
    2. Rule-based Fallback (Immediate if agent fails)
    """
    try:
        # print(f"[STEP] Suitability Analysis Started...")
        
        # Convert Pydantic to dict
        survey = request.dict()
        
        # 1. Try Agent Analysis
        try:
            from agent_engine.fund_crew import run_suitability_analysis
            # print(f"[INFO] Running Agent Suitability Analysis...")
            result = run_suitability_analysis(survey, model_name="gpt-4o")
            # print(f"[SUCCESS] Agent-based Suitability Analysis Complete")
            
            # [Safety Check] Ensure essential keys exist
            if "ips" not in result: 
                result["ips"] = {}
            if "decision_profile" not in result:
                result["decision_profile"] = {}
                
            # Fill defaults if missing
            _fill_ips_defaults(result["ips"], survey)
            
            return result
            
        except Exception as agent_error:
            print(f"[WARNING] Agent analysis failed/timeout: {agent_error}. Using Rule-based Fallback.")
            # Fall through to fallback
            
        # 2. Rule-based Fallback
        risk_level = 3
        loss_tol = survey.get('max_loss_tolerance_pct', 20)
        
        if loss_tol >= 30: risk_level = 5
        elif loss_tol >= 20: risk_level = 4
        elif loss_tol >= 15: risk_level = 3
        elif loss_tol >= 10: risk_level = 2
        else: risk_level = 1
        
        # IPS Generation
        ips = {
            "risk_level": risk_level,
            "horizon_months": survey.get('investment_period_months', 36),
            "target_vol": 0.10 + (risk_level * 0.02),
            "max_drawdown_target": loss_tol / 100.0,
            "cvar_limit_95": (loss_tol / 100.0) * 0.8,
            "equity_range": [0.2 + (risk_level * 0.1), 0.4 + (risk_level * 0.1)],
            "rebalance_band": 0.05
        }
        
        # Profile Generation
        decision_profile = {
            "risk_capacity": {
                "assessment": "안정적" if survey.get('income_stability') == 'stable' else "변동적",
                "score": risk_level
            },
            "risk_preference": {
                "assessment": "공격적" if risk_level >= 4 else "중립적",
                "score": risk_level
            },
            "decision_style": {
                "type": "Rule-Based",
                "assessment": "데이터 기반의 체계적 투자 선호"
            }
        }
        
        return {
            "decision_profile": decision_profile,
            "ips": ips,
            "profile_summary": f"위험 성향 Level {risk_level} (Rule-Based Generated)",
            "key_insights": [
                "시스템 장애로 인해 룰 기반 분석이 적용되었습니다.",
                f"손실 허용 한도 {loss_tol}%를 준수하는 포트폴리오를 제안합니다.",
                "안정적인 장기 성과를 목표로 합니다."
            ],
            "_fallback": True
        }
        
    except Exception as e:
        print(f"[ERROR] Suitability Analysis Critical Failure: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _fill_ips_defaults(ips, survey):
    defaults = {
        "risk_level": 3,
        "target_vol": 0.15,
        "max_drawdown_target": 0.20,
        "cvar_limit_95": 0.15,
        "equity_range": [0.3, 0.7],
        "rebalance_band": 0.05
    }
    for k, v in defaults.items():
        if k not in ips or ips[k] is None:
            ips[k] = v
            
    # Normalize types
    if "target_vol_annual" in ips: ips["target_vol"] = ips["target_vol_annual"]
    if not isinstance(ips.get("equity_range"), list): ips["equity_range"] = defaults["equity_range"]


@router.post("/universe")
def build_universe(request: UniverseRequest):
    """
    투자 유니버스 구성
    Returns a list of assets (Stocks/ETFs) with metrics.
    Robustness: Falls back to mock data if yfinance fails.
    """
    # print(f"[INFO] Universe Construction Started...")
    
    # 1. Define Candidates (Rich List)
    candidates = _get_candidate_list()
    
    # Add user holdings provided in request
    if request.user_holdings:
        existing_tickers = {c['ticker'] for c in candidates}
        for h in request.user_holdings:
            if h.ticker not in existing_tickers:
                candidates.append({
                    "ticker": h.ticker, 
                    "name": h.name or h.ticker, 
                    "asset_type": "stock", 
                    "region": "KR" if ".KS" in h.ticker or ".KQ" in h.ticker else "US", 
                    "sector": "User Holding"
                })

    tickers = [c['ticker'] for c in candidates]
    
    try:
        # 2. Try Fetching Real Data
        # print(f"[INFO] Attempting to fetch market data using yfinance for {len(tickers)} tickers...")
        
        # Fetch logic wrapped for safety
        market_stats = _fetch_market_stats_safe(tickers)
        
        final_universe = []
        is_mock_mode = len(market_stats) == 0
        
        # 3. Merge Data
        for cand in candidates:
            stat = market_stats.get(cand['ticker'])
            
            cand_data = cand.copy()
            if stat:
                cand_data.update(stat)
            else:
                # If single ticker fetch failed or global failure
                cand_data.update(_generate_mock_stats(cand['ticker']))
                if is_mock_mode:
                    cand_data['_is_mock'] = True
            
            final_universe.append(cand_data)
            
        # 4. Filter & Select Logic (Rule-Based Smart Selection)
        # Always include 'Must Haves' (Market Indices, Safe Assets)
        must_haves = ['SPY', 'QQQ', 'TLT', 'GLD', '005930.KS']
        if request.user_holdings:
            must_haves.extend([h.ticker for h in request.user_holdings])
            
        selected_universe = []
        
        # Add Must Haves
        for item in final_universe:
            if item['ticker'] in must_haves:
                item['rationale'] = "Core Asset / User Holding"
                selected_universe.append(item)
                
        # Add Top Momentum Assets (from remaining)
        remaining = [x for x in final_universe if x['ticker'] not in must_haves]
        remaining.sort(key=lambda x: x.get('momentum_1m', 0), reverse=True)
        
        # Select Top 7 from remaining
        top_picks = remaining[:7]
        for item in top_picks:
            item['rationale'] = f"High Momentum (1M: {item.get('momentum_1m', 0)*100:.1f}%)"
            selected_universe.append(item)
            
        # Stats
        stats = {
            "total_count": len(selected_universe),
            "stock_count": sum(1 for u in selected_universe if u['asset_type'] == 'stock'),
            "etf_count": sum(1 for u in selected_universe if u['asset_type'] == 'etf'),
            "is_simulated": is_mock_mode
        }
        
        # print(f"[SUCCESS] Universe Built. Count: {stats['total_count']}. Simulated: {stats['is_simulated']}")
        return {
            "universe": selected_universe,
            "stats": stats
        }

    except Exception as e:
        print(f"[ERROR] Universe Construction Failed: {e}")
        # Absolute Fallback: Return Mock Universe
        print("[WARN] Using Emergency Mock Universe")
        mock_universe = _get_fallback_universe()
        return {
            "universe": mock_universe,
            "stats": {"total_count": len(mock_universe), "note": "Emergency Fallback"}
        }

def _fetch_market_stats_safe(tickers: List[str]) -> Dict[str, dict]:
    """Safe Fetch Returns {ticker: {volatility, return, momentum}}"""
    results = {}
    if not tickers: return results
    
    try:
        # Batch download
        # period="6mo" usually ample
        data = yf.download(tickers, period="6mo", progress=False, auto_adjust=True, threads=False)
        
        if data is None or data.empty:
            raise ValueError("Empty data returned from yfinance")
            
        close_data = None
        
        # Scenario A: MultiIndex (Expected for list of tickers with len > 1)
        if isinstance(data.columns, pd.MultiIndex):
            try:
                close_data = data['Close']
            except KeyError:
                try: close_data = data['Adj Close'] 
                except KeyError: pass
        
        # Scenario B: Single Index (If only 1 ticker was valid, columns are OHLC)
        else:
             if 'Close' in data.columns:
                 # Data is a DataFrame with Open, High, Low, Close
                 # But we don't know WHICH ticker it is if we passed multiple and only 1 returned.
                 # Usually yfinance returns a MultiIndex if we passed a list.
                 # If we passed list of length 1, it returns Single Index.
                 if len(tickers) == 1:
                     close_data = pd.DataFrame({tickers[0]: data['Close']})
                 else:
                     # Ambiguous fallback
                     pass
                 
        if close_data is None or close_data.empty:
            raise ValueError("Could not extract Close data")
            
        # Calculate stats for each column (ticker)
        for ticker in close_data.columns:
            series = close_data[ticker].dropna()
            if len(series) < 20: continue
            
            # Calcs
            ret_series = series.pct_change().dropna()
            vol = float(ret_series.std() * np.sqrt(252))
            total_ret = float((series.iloc[-1] / series.iloc[0]) - 1)
            
            # Momentum (1m) approx 20 days
            if len(series) >= 20:
                mom_1m = float((series.iloc[-1] / series.iloc[-20]) - 1)
            else:
                mom_1m = 0.0
                
            results[ticker] = {
                "avg_volatility_1y": vol,
                "avg_return_1y": total_ret,
                "momentum_1m": mom_1m,
                "curr_price": float(series.iloc[-1])
            }
            
    except Exception as e:
        print(f"[WARN] Batch fetch failed ({e})...")
        pass
        
    return results

def _generate_mock_stats(ticker):
    """Generate plausible random stats for fallback"""
    is_safe = ticker in ['TLT', 'IEF', 'BND', 'SHy']
    vol = random.uniform(0.05, 0.15) if is_safe else random.uniform(0.15, 0.40)
    ret = random.uniform(0.0, 0.10) if is_safe else random.uniform(-0.10, 0.30)
    mom = random.uniform(0.0, 0.05) if is_safe else random.uniform(-0.05, 0.15)
    
    return {
        "avg_volatility_1y": vol,
        "avg_return_1y": ret,
        "momentum_1m": mom,
        "curr_price": 100.0,
        "_is_mock": True
    }

def _get_candidate_list():
    return [
        {"ticker": "005930.KS", "name": "삼성전자", "asset_type": "stock", "region": "KR", "sector": "Technology"},
        {"ticker": "000660.KS", "name": "SK하이닉스", "asset_type": "stock", "region": "KR", "sector": "Technology"},
        {"ticker": "035420.KS", "name": "NAVER", "asset_type": "stock", "region": "KR", "sector": "Communication"},
        {"ticker": "035720.KS", "name": "카카오", "asset_type": "stock", "region": "KR", "sector": "Communication"},
        {"ticker": "005380.KS", "name": "현대차", "asset_type": "stock", "region": "KR", "sector": "Consumer"},
        {"ticker": "105560.KS", "name": "KB금융", "asset_type": "stock", "region": "KR", "sector": "Financial"},
        {"ticker": "373220.KS", "name": "LG에너지솔루션", "asset_type": "stock", "region": "KR", "sector": "Energy"},
        {"ticker": "SPY", "name": "SPDR S&P 500", "asset_type": "etf", "region": "US", "sector": "Market"},
        {"ticker": "QQQ", "name": "Invesco QQQ", "asset_type": "etf", "region": "US", "sector": "Technology"},
        {"ticker": "TLT", "name": "iShares 20Y+ Treasury", "asset_type": "etf", "region": "US", "sector": "Fixed Income"},
        {"ticker": "GLD", "name": "SPDR Gold Shares", "asset_type": "etf", "region": "US", "sector": "Commodity"},
        {"ticker": "NVDA", "name": "NVIDIA", "asset_type": "stock", "region": "US", "sector": "Technology"},
        {"ticker": "AAPL", "name": "Apple Inc.", "asset_type": "stock", "region": "US", "sector": "Technology"},
        {"ticker": "MSFT", "name": "Microsoft", "asset_type": "stock", "region": "US", "sector": "Technology"},
        {"ticker": "TSLA", "name": "Tesla", "asset_type": "stock", "region": "US", "sector": "Consumer"},
        {"ticker": "GOOGL", "name": "Alphabet (Google)", "asset_type": "stock", "region": "US", "sector": "Communication"},
        {"ticker": "AMZN", "name": "Amazon", "asset_type": "stock", "region": "US", "sector": "Consumer"},
    ]

def _get_fallback_universe():
    """Returns a purely static universe for emergencies"""
    base = _get_candidate_list()
    for item in base:
        item.update(_generate_mock_stats(item['ticker']))
        item['rationale'] = "System Fallback Asset"
    return base[:10]


@router.post("/construct")
def construct_portfolios(request: ConstructionRequest):
    """
    3가지 포트폴리오 생성
    Robust Mode: guarantees output
    """
    # print(f"[INFO] Portfolio Construction Started...")
    try:
        universe = request.universe
        if not universe:
            print("[WARN] Empty universe received, using fallback.")
            universe = _get_fallback_universe()
            
        ips = request.ips or {}
        
        # Calculate Base Capital
        initial_cash = request.initial_capital or 0
        holdings_val = sum(h.amount for h in request.user_holdings) if request.user_holdings else 0
        total_aum = initial_cash + holdings_val
        if total_aum <= 0: total_aum = 10000000 
        
        # Parameters
        equity_range = ips.get("equity_range", [0.4, 0.8])
        if not isinstance(equity_range, list): equity_range = [0.4, 0.8]
        min_eq, max_eq = equity_range[0], equity_range[1]
        
        scenarios = [
            ("Core-Satellite", "핵심-위성 전략 (균형 성장)", (min_eq + max_eq)/2),
            ("Momentum-Alpha", "시장 주도주 집중 (적극 투자)", max_eq),
            ("Defensive-Yield", "배당/채권 중심 (자산 방어)", min_eq)
        ]
        
        portfolios = []
        
        for name, desc, eq_ratio in scenarios:
            portfolios.append(_build_single_portfolio(name, desc, eq_ratio, universe, total_aum, ips))
            
        # print(f"[SUCCESS] 3 Portfolios Generated.")
        return {
            "portfolios": portfolios,
            "construction_log": {"method": "Robust Dynamic Allocation", "timestamp": str(datetime.now())}
        }
        
    except Exception as e:
        print(f"[ERROR] Portfolio Construction Failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Construction Error")

def _build_single_portfolio(name, desc, eq_target, universe, total_amount, ips):
    """Builds one portfolio dict"""
    
    # Split
    safes = [u for u in universe if u['asset_type'] == 'etf' and u['ticker'] in ['TLT', 'IEF', 'BND', 'GLD']]
    stocks = [u for u in universe if u not in safes]
    
    if not safes: safes = universe[:2] 
    if not stocks: stocks = universe[2:]
    
    # Allocate
    holdings = []
    
    # Equity
    stock_portion = total_amount * eq_target
    if len(stocks) > 0:
        w_per_stock = stock_portion / len(stocks)
        for s in stocks:
            holdings.append({
                "ticker": s['ticker'],
                "name": s['name'],
                "amount_krw": w_per_stock,
                "weight": w_per_stock / total_amount,
                "asset_type": s["asset_type"],
                "region": s["region"],
                "rationale": f"{name} Strategy Allocation"
            })
            
    # Safe
    safe_portion = total_amount * (1 - eq_target)
    if len(safes) > 0:
        w_per_safe = safe_portion / len(safes)
        for s in safes:
            holdings.append({
                "ticker": s['ticker'],
                "name": s['name'],
                "amount_krw": w_per_safe,
                "weight": w_per_safe / total_amount,
                "asset_type": s["asset_type"],
                "region": s["region"],
                "rationale": "Risk Hedging"
            })
            
    # Calc
    w_eq = sum(h['weight'] for h in holdings if h['ticker'] in [x['ticker'] for x in stocks])
    w_safe = sum(h['weight'] for h in holdings if h['ticker'] in [x['ticker'] for x in safes])
    
    exp_ret = (w_eq * 0.12) + (w_safe * 0.04)
    vol = (w_eq * 0.20) + (w_safe * 0.05)
    
    return {
        "name": name,
        "description": desc,
        "holdings": holdings,
        "total_holdings_count": len(holdings),
        "domestic_weight": sum(h['weight'] for h in holdings if h['region'] == 'KR'),
        "overseas_weight": sum(h['weight'] for h in holdings if h['region'] != 'KR'),
        "forecast": {
            "return_p50": exp_ret,
            "volatility": vol,
            "goal_achievement_prob": 0.5 + (exp_ret * 2),
            "max_drawdown_est": -2.0 * vol
        },
        "explainability": {
            "why_this_portfolio": [
                f"{desc} 표방하여 주식 비중을 {int(eq_target*100)}%로 설정했습니다.",
                "성장성과 안정성의 균형을 위한 Smart Beta 전략입니다."
            ],
            "risk_summary": {
                "market": "시장 하락시 변동성 확대 주의",
                "currency": "환율 변동이 자산 가치에 영향을 줄 수 있음",
                "liquidity": "유동성이 풍부한 대형주 위주 구성",
                "strategy": "주기적인 리밸런싱 필요"
            },
            "what_to_watch": ["거시 경제 지표(금리, 인플레)", "주요 기술주 실적"]
        }
    }
