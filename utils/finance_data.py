# utils/finance_data.py
# 가격 데이터, RSI, 수익률, 기대수익률
# - 미국/글로벌: yfinance
# - 국내 개별 종목(6자리 숫자): 한국투자증권 KIS 일별시세 API 우선 사용

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import yfinance as yf

# KIS 일별 시세 헬퍼 (없어도 동작하도록 예외 처리)
try:
    from utils.kis_api import get_daily_price_history  # type: ignore
except Exception:  # ImportError, RuntimeError 등 포함
    get_daily_price_history = None  # type: ignore[assignment]


# ───────────────────────
# 국내/해외 티커 판별 & 기간 계산
# ───────────────────────

def _is_korea_stock_symbol(ticker: str) -> bool:
    """
    국내 주식 티커 판단:
    - 6자리 숫자 (예: 005930, 000660 등)
    """
    t = str(ticker).strip()
    return len(t) == 6 and t.isdigit()


def _period_to_dates(period: str) -> tuple[str, str]:
    """
    '3mo', '6mo', '1y', '30d' 같은 period 문자열을
    (시작일, 종료일) 'YYYYMMDD' 튜플로 변환.
    """
    today = datetime.today().date()

    p = (period or "").lower()
    days = 365  # 기본 1년

    if p.endswith("mo"):
        try:
            n = int(p[:-2] or "0")
            days = n * 30
        except ValueError:
            pass
    elif p.endswith("y"):
        try:
            n = int(p[:-1] or "0")
            days = n * 365
        except ValueError:
            pass
    elif p.endswith("d"):
        try:
            n = int(p[:-1] or "0")
            days = n
        except ValueError:
            pass

    start = today - timedelta(days=days)
    return start.strftime("%Y%m%d"), today.strftime("%Y%m%d")


# ───────────────────────
# pykrx 기반 국내 주식 히스토리
# ───────────────────────

def _fetch_pykrx_price_history(
    ticker: str,
    period: str = "3mo",
) -> pd.DataFrame:
    """
    pykrx를 사용하여 한국거래소에서 일별 시세 조회.
    [date index, 'close' 컬럼] 형태의 DataFrame 반환.
    
    - pykrx 없거나 에러 → 빈 DataFrame 반환
    """
    try:
        from pykrx import stock as krx_stock
    except ImportError:
        return pd.DataFrame(columns=["close"])

    try:
        start, end = _period_to_dates(period)
        # pykrx는 YYYYMMDD 문자열을 그대로 받음
        df = krx_stock.get_market_ohlcv_by_date(start, end, ticker)
        
        if df is None or df.empty:
            return pd.DataFrame(columns=["close"])
        
        # pykrx는 이미 날짜를 인덱스로 반환하고, 컬럼명이 한글 (종가, 시가 등)
        # 종가 컬럼 찾기
        if "종가" in df.columns:
            df = df.rename(columns={"종가": "close"})
        elif "Close" in df.columns:
            df = df.rename(columns={"Close": "close"})
        else:
            return pd.DataFrame(columns=["close"])
        
        return df[["close"]].copy()
        
    except Exception as e:
        print(f"[_fetch_pykrx_price_history] pykrx 조회 실패 ({ticker}): {e}")
        return pd.DataFrame(columns=["close"])


# ───────────────────────
# 통합 히스토리 조회 (국내: pykrx 우선, 해외: yfinance)
# ───────────────────────

def fetch_price_history(ticker: str, period: str = "3mo", interval: str = "1d") -> pd.DataFrame:
    """
    가격 히스토리 통합 함수.

    - 국내 개별 종목(6자리 숫자): pykrx 우선 사용
      · pykrx 실패 시 yfinance(티커.KS)로 Fallback
    - 그 외(미국 종목, 지수 등): yfinance 그대로 사용

    반환:
      - 항상 'close' 컬럼 하나만 가진 DataFrame
      - 실패/데이터 없음 → 빈 DataFrame(columns=['close'])
    """
    symbol = str(ticker).strip()

    # 1) 국내 개별 종목이면 pykrx 우선
    yf_symbol = symbol
    if _is_korea_stock_symbol(symbol):
        df_krx = _fetch_pykrx_price_history(symbol, period=period)
        if df_krx is not None and not df_krx.empty:
            print(f"[fetch_price_history] pykrx로 {ticker} 조회 성공: {len(df_krx)} rows")
            return df_krx

        # pykrx에서 못 가져온 경우에만 yfinance Fallback (.KS)
        print(f"[fetch_price_history] pykrx 실패, yfinance로 폴백: {ticker}")
        yf_symbol = f"{symbol}.KS"

    # 2) yfinance로 히스토리 조회
    try:
        df = yf.download(
            yf_symbol,
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False,
        )
    except Exception as e:
        print(f"[fetch_price_history] yfinance 다운로드 실패 ({yf_symbol}): {e}")
        return pd.DataFrame(columns=["close"])

    if df is None or df.empty:
        return pd.DataFrame(columns=["close"])

    # 🔹 MultiIndex 컬럼 평탄화 (yfinance 최신 버전 대응)
    # 예: columns가 MultiIndex([('Close', '005930.KS')], names=['Price', 'Ticker']) 인 경우
    #     -> Index(['Close'], name='Price') 로 변경
    if isinstance(df.columns, pd.MultiIndex):
        try:
            # 보통 level 0이 Price Type (Close, Open...)
            df.columns = df.columns.get_level_values(0)
        except Exception:
            pass

    if "Close" in df.columns:
        df = df.rename(columns={"Close": "close"})
    elif "Adj Close" in df.columns:
        df = df.rename(columns={"Adj Close": "close"})
    elif "close" not in df.columns:
        # If neither Close nor Adj Close nor close exists, return empty
        return pd.DataFrame(columns=["close"])

    print(f"[fetch_price_history] yfinance로 {yf_symbol} 조회 성공: {len(df)} rows")
    return df[["close"]].copy()


# ───────────────────────
# 수익률 / RSI / 3개월 기대수익률
# ───────────────────────

def compute_returns(df: pd.DataFrame, days: int) -> float:
    """
    최근 기준 'days' 거래일 전 대비 수익률(%).

    데이터가 부족하면 NaN 반환.
    """
    if df.empty or len(df) < days + 1:
        return math.nan
    recent = df["close"].iloc[-1]
    past = df["close"].iloc[-(days + 1)]
    return (recent / past - 1) * 100.0


def compute_rsi(series: pd.Series, period: int = 14) -> float:
    """
    단순 RSI 계산 (지수이평 아님).
    """
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / (avg_loss + 1e-9)
    rsi = 100 - (100 / (1 + rs))
    return float(rsi.iloc[-1])


def estimate_3m_outlook(
    df_ticker: pd.DataFrame,
    df_bench: Optional[pd.DataFrame] = None,
):
    """
    단순 평균 일간 수익률 기반 3개월 기대수익률 / 초과수익 추정.
    """
    if df_ticker is None or df_ticker.empty:
        return None, None

    ret_t = df_ticker["close"].pct_change().dropna()
    if len(ret_t) < 40:
        return None, None

    mean_t = ret_t.mean()
    horizon_days = 63  # 약 3개월 거래일수
    exp_t_3m = (1 + mean_t) ** horizon_days - 1

    exp_b_3m = None
    if df_bench is not None and not df_bench.empty:
        ret_b = df_bench["close"].pct_change().dropna()
        if len(ret_b) >= 40:
            mean_b = ret_b.mean()
            exp_b_3m = (1 + mean_b) ** horizon_days - 1

    exp_t_3m_pct = exp_t_3m * 100
    alpha_3m_pct = (exp_t_3m - exp_b_3m) * 100 if exp_b_3m is not None else None
    return exp_t_3m_pct, alpha_3m_pct


# ───────────────────────
# 펀더멘털 데이터 조회
# ───────────────────────

def fetch_fundamentals(ticker: str) -> dict:
    """
    주요 펀더멘털 지표 조회.
    
    **한국 종목 (6자리 숫자 or .KS/.KQ):**
    - KIS API: PER, PBR, ROE, EPS, BPS (실시간/정확)
    - DART API: 부채비율, 매출성장률, 영업이익률 (재무제표 기반)
    
    **미국/글로벌 종목:**
    - yfinance 사용
    """
    symbol = str(ticker).strip()
    korea_code = None

    # 1) 국내 종목 코드 식별
    if _is_korea_stock_symbol(symbol):
        korea_code = symbol
    elif symbol.endswith(".KS") or symbol.endswith(".KQ"):
        base = symbol[:-3]
        if _is_korea_stock_symbol(base):
            korea_code = base

    # 2) 한국 종목이면 KIS API + DART API 사용
    if korea_code:
        # A. KIS API로 주가 지표 조회 (PER, PBR, ROE)
        kis_data = {}
        try:
            from utils.kis_api import get_market_metrics
            kis_data = get_market_metrics(korea_code)
        except Exception as e:
            print(f"[fetch_fundamentals] KIS API 조회 실패 ({korea_code}): {e}")
        
        # B. DART API로 재무제표 지표 조회 (부채비율, 성장률, 이익률)
        dart_data = {}
        try:
            from utils.dart_fundamentals import DartFinancialAPI
            dart = DartFinancialAPI()
            dart_data = dart.calculate_fundamentals(korea_code)
        except Exception as e:
            print(f"[fetch_fundamentals] DART API 조회 실패 ({korea_code}): {e}")
        
        # 두 소스 결합
        return {
            # KIS API 데이터 (우선순위 높음: 실시간성)
            "pe": kis_data.get("per"),
            "pb": kis_data.get("pbr"),
            "roe": kis_data.get("roe"), # KIS ROE 사용 (DART보다 신뢰성 높음)
            "eps": kis_data.get("eps"),
            "bps": kis_data.get("bps"),
            "dividend_yield": None, 
            
            # DART API 데이터 (보조: 성장률, 안정성)
            "revenue_growth_yoy": dart_data.get("revenue_growth_yoy"), # 없으면 None
            "operating_margin": dart_data.get("operating_margin"),
            "debt_to_equity": dart_data.get("debt_to_equity"),
        }

    # 3) 미국/글로벌 종목은 yfinance 사용
    try:
        t = yf.Ticker(symbol)
        info = t.info or {}

        # Validate Dividend Yield (0% ~ 20%)
        d_yield = info.get("dividendYield")
        if d_yield is not None:
             try:
                 val = float(d_yield)
                 if val < 0 or val > 0.20:
                     d_yield = None
             except:
                 d_yield = None

        return {
            "revenue_growth_yoy": info.get("revenueGrowth"),
            "operating_margin": info.get("operatingMargins"),
            "roe": info.get("returnOnEquity"),
            "debt_to_equity": info.get("debtToEquity"),
            "pe": info.get("trailingPE") or info.get("forwardPE"),
            "pb": info.get("priceToBook"),
            "dividend_yield": d_yield,
            "eps": info.get("trailingEps"),
            "bps": info.get("bookValue"),
            "target_mean_price": info.get("targetMeanPrice"),
            "peg_ratio": info.get("pegRatio"),
            "earnings_growth": info.get("earningsGrowth"),
            "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
        }
    except Exception as e:
        print(f"[fetch_fundamentals] yfinance 실패 ({symbol}): {e}")
        return {
            "pe": None, "pb": None, "roe": None,
            "eps": None, "bps": None, "dividend_yield": None,
            "revenue_growth_yoy": None, "operating_margin": None, "debt_to_equity": None,
        }

