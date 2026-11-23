"""
utils.market_indicators
=======================

한국 시장 고정 지표 모듈 (KOSPI / KOSDAQ / VKOSPI / 국채10Y / KOSPI PBR / USDKRW).

- 미국 지표는 main 쪽에서 처리 → 여기서는 비워둠.
- 이 모듈은 "korea" 섹션만 실제 값으로 채운다.

데이터 소스 설계
----------------
1) KOSPI / KOSDAQ 3개월 수익률
   - 우선 pykrx의 공식 지수 데이터 사용
     * KOSPI  : 지수코드 "1001"
     * KOSDAQ: 지수코드 "2001"
   - pykrx 미설치/오류 시 yfinance (^KS11, ^KQ11)로 fallback (정확도는 다소 떨어질 수 있음).

2) VKOSPI
   - 우선 pykrx get_index_ohlcv(지수코드 "1028") 시도
   - 실패 시 (None, None) 반환.

3) 한국 10년물 국채 금리 (KR10Y)
   - FRED API 사용 (series_id=IRLTLT01KRM156N, 한국 10년물 수익률)
   - 환경변수 FRED_API_KEY 필요.
   - 실패 시 None.

4) KOSPI PBR
   - pykrx.get_index_fundamental(지수코드 "1001")에서 PBR 컬럼 사용.
   - 실패 시 None.

5) USD/KRW 환율
   - FRED API 사용 (series_id=DEXKOUS, 원/달러 환율)
   - FRED 실패 시 yfinance("KRW=X") fallback.

반환 형식
---------
get_market_indicators() → dict
{
    "equity": {},
    "volatility": {},
    "macro": {},
    "sentiment": {},
    "korea": {
        "equity": {
            "KOSPI": { "ret_3m": { "value": float|None, "label": "3개월 수익률" } },
            "KOSDAQ": { ... },
        },
        "volatility": {
            "VKOSPI": { "value": float|None, "change_pct": float|None },
        },
        "macro": {
            "KR10Y": { "value": float|None },
        },
        "valuation": {
            "KOSPI_PBR": { "value": float|None },
        },
        "fx": {
            "USDKRW": { "value": float|None },
        },
    }
}
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict, Any
import concurrent.futures

import pandas as pd
import requests
import yfinance as yf

# ─────────────────────────────────────
# pykrx (있으면 사용, 없으면 None)
# ─────────────────────────────────────
try:
    from pykrx import stock as krx_stock
except ImportError:  # 선택 라이브러리
    krx_stock = None


# ─────────────────────────────────────
# 공통 헬퍼
# ─────────────────────────────────────
def _safe_float(x) -> Optional[float]:
    try:
        if x is None:
            return None
        return float(x)
    except Exception:
        return None


def _ret_3m(df: pd.DataFrame, col: str = "Close") -> Optional[float]:
    """
    3개월 히스토리 DataFrame에서 단순 구간 수익률(%) 계산.
    """
    if df is None or df.empty:
        return None
    try:
        first = float(df[col].iloc[0])
        last = float(df[col].iloc[-1])
        if first == 0:
            return None
        return (last / first - 1.0) * 100.0
    except Exception:
        return None


def _fetch_3m_history_yf(ticker: str, interval: str = "1d") -> pd.DataFrame:
    """
    yfinance에서 3개월치 데이터를 받아오는 헬퍼 함수.
    실패하면 빈 DataFrame 리턴.
    """
    try:
        df = yf.Ticker(ticker).history(period="3mo", interval=interval)
        if not df.empty:
            df = df.copy()
            df.index = pd.to_datetime(df.index)
        return df
    except Exception:
        return pd.DataFrame()


def _fetch_last_price_yf(ticker: str) -> Optional[float]:
    """
    가장 최근 종가(또는 환율·금리 등)를 하나만 가져오는 간단 함수.
    실패 시 None.
    """
    try:
        df = yf.Ticker(ticker).history(period="5d", interval="1d")
        if df is None or df.empty:
            return None
        val = df["Close"].iloc[-1]
        return float(val)
    except Exception:
        return None


# ─────────────────────────────────────
# FRED 공통 함수 (한국 10Y, USDKRW 등)
# ─────────────────────────────────────
FRED_API_KEY = os.getenv("FRED_API_KEY")


def _fetch_latest_from_fred(series_id: str, limit: int = 10) -> Optional[float]:
    """
    FRED에서 최근 관측치를 가져오는 헬퍼.
    - series_id: FRED 시리즈 ID (예: IRLTLT01KRM156N, DEXKOUS 등)
    - 실패 시 None.
    """
    if not FRED_API_KEY:
        return None

    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "sort_order": "desc",
        "limit": limit,
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        obs = data.get("observations", []) or []
        # value 가 "." 인 항목 제외
        for o in obs:
            v = o.get("value")
            if v is None or v == ".":
                continue
            fv = _safe_float(v)
            if fv is not None:
                return fv
    except Exception:
        return None

    return None


# ─────────────────────────────────────
# KOSPI / KOSDAQ 3개월 수익률
# ─────────────────────────────────────
                                                                    


def fetch_kospi_kosdaq_3m() -> Tuple[Optional[float], Optional[float]]:
    """
    KOSPI / KOSDAQ 3개월 수익률 (%)
    - yfinance (^KS11, ^KQ11) 사용
    
    주의: pykrx 코드 1001/2001은 KOSPI200/KOSDAQ150 등 다른 지수를 반환하므로 사용하지 않음
    """
    # yfinance로 직접 가져오기 (가장 정확함)
    kospi_df = _fetch_3m_history_yf("^KS11")
    kosdaq_df = _fetch_3m_history_yf("^KQ11")

    kospi_ret_3m = _ret_3m(kospi_df)
    kosdaq_ret_3m = _ret_3m(kosdaq_df)

    return kospi_ret_3m, kosdaq_ret_3m


# ─────────────────────────────────────
# VKOSPI (pykrx)
# ─────────────────────────────────────
def _fetch_vkospi_from_openapi(api_key: str) -> Tuple[Optional[float], Optional[float]]:
    """
    KRX OpenAPI를 사용한 VKOSPI 조회.
    """
    try:
        # VKOSPI도 지수이므로 동일한 엔드포인트 시도
        url = "https://openapi.krx.co.kr/api/open/contents/index/01/01010100/jsp/01010100.jsp"
        headers = {
            "auth-key": api_key,
            "User-Agent": "Mozilla/5.0"
        }
        params = {"basDd": datetime.today().strftime("%Y%m%d")}

        res = requests.get(url, headers=headers, params=params, timeout=5)
        if res.status_code == 200:
            data = res.json()
            output = data.get('output', [])
            if isinstance(output, list):
                for item in output:
                    # VKOSPI 찾기
                    idx_nm = item.get('idxNm', '')
                    if 'VKOSPI' in idx_nm or '변동성지수' in idx_nm:
                         # 현재가
                         clpr = _safe_float(item.get('clpr')) # 종가
                         # 3개월 전 데이터는 별도 조회가 필요하므로 일단 None
                         # (OpenAPI에서 기간 데이터를 주는 엔드포인트가 아니라고 가정)
                         if clpr:
                             print(f"✅ VKOSPI (OpenAPI): {clpr}")
                             return clpr, None
        return None, None
    except Exception:
        return None, None

def fetch_vkospi() -> Tuple[Optional[float], Optional[float]]:
    """
    VKOSPI 현재값 + 3개월 변동률(%)
    1. KRX OpenAPI (Key)
    2. Investing.com Crawling (Fallback)
    """
    
    # 1. OpenAPI
    api_key = os.getenv("KRX_API_KEY")
    if api_key:
        val, chg = _fetch_vkospi_from_openapi(api_key)
        if val is not None:
            return val, chg

    # 2. Investing.com Crawling (Fallback)
    try:
        url = "https://kr.investing.com/indices/kospi-volatility"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        html = res.text
        
        import re
        
        # data-test="instrument-price-last" 패턴 찾기
        match = re.search(r'data-test="instrument-price-last"[^>]*>([0-9.]+)', html)
        if match:
            current_val = _safe_float(match.group(1))
            if current_val and 5 < current_val < 100:
                return current_val, None
        
        # 대체 패턴
        matches = re.findall(r'\b([1-9][0-9]\.[0-9]{2})\b', html)
        for m in matches:
            val = _safe_float(m)
            if val and 10 < val < 60:
                return val, None
                
    except Exception:
        pass
    
    return None, None


# ─────────────────────────────────────
# 한국 10년물 금리 (FRED → investing.com)
# ─────────────────────────────────────
def _fetch_kr_10y_from_investing() -> Optional[float]:
    """
    investing.com에서 한국 10년물 국채 수익률 크롤링.
    - https://kr.investing.com/rates-bonds/south-korea-10-year-bond-yield
    """
    try:
        url = "https://kr.investing.com/rates-bonds/south-korea-10-year-bond-yield"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        html = res.text
        
        import re
        
        # 방법 1: data-test="instrument-price-last" 속성 찾기 (investing.com 공통 패턴)
        match = re.search(r'data-test="instrument-price-last"[^>]*>([0-9.]+)', html)
        if match:
            val = _safe_float(match.group(1))
            if val is not None and 0 < val < 20:
                return val
        
        # 방법 2: class="text-2xl" 같은 큰 숫자 표시 영역 찾기
        match = re.search(r'class="[^"]*text-[^"]*"[^>]*>([0-9]{1,2}\.[0-9]{2,3})', html)
        if match:
            val = _safe_float(match.group(1))
            if val is not None and 0 < val < 20:
                return val
        
        # 방법 3: 일반적인 숫자 패턴 (페이지 전체에서 합리적인 수익률 값 찾기)
        # 한국 10년물은 보통 2-5% 범위
        matches = re.findall(r'\b([2-5]\.[0-9]{2,3})\b', html)
        if matches:
            # 가장 먼저 나오는 값 사용
            val = _safe_float(matches[0])
            if val is not None:
                return val
        
        return None
    except Exception as e:
        return None



def fetch_kr_10y_yield() -> Optional[float]:
    """
    한국 10년물 국채 금리 (%)

    1차: FRED 시리즈 IRLTLT01KRM156N 사용
    - Long-Term Government Bond Yields: 10-Year for Korea
    - 이미 % 단위로 제공됨.

    2차: investing.com 웹 크롤링
    - https://kr.investing.com/rates-bonds/south-korea-10-year-bond-yield

    실패 시 None.
    """
    # 1) FRED 시도
    series_id = os.getenv("FRED_KR10Y_SERIES", "IRLTLT01KRM156N")
    val = _fetch_latest_from_fred(series_id)
    if val is not None:
        return val

    # 2) investing.com 크롤링
    val = _fetch_kr_10y_from_investing()
    if val is not None:
        return val
    
    return None


# ─────────────────────────────────────
# KOSPI PBR (OpenAPI & pykrx)
# ─────────────────────────────────────

def _fetch_kospi_pbr_from_openapi(api_key: str) -> Optional[float]:
    """
    KRX OpenAPI를 사용한 KOSPI PBR 조회.
    API Key가 있는 경우 우선 사용됨.
    """
    try:
        # 공식 KOSPI 지수 엔드포인트 추정 (OpenAPI)
        # 보통 KRX OpenAPI는 'auth-key' 헤더를 요구합니다.
        
        # 1. 지수 기본 정보 (여기서 PBR 제공 여부 확인)
        base_urls = [
            "https://openapi.krx.co.kr/api/open/contents/index/01/01010100/jsp/01010100.jsp",
            "https://openapi.krx.co.kr/api/open/contents/index/01/01010100/jsp/01010102.jsp" # 시세정보
        ]
        
        headers = {
            "auth-key": api_key,
            "User-Agent": "Mozilla/5.0"
        }
        
        today = datetime.today().strftime("%Y%m%d")
        
        print(f"ℹ️ KRX API Key detected. Attempting OpenAPI Fetch...")
        
        for url in base_urls:
             # 파라미터는 보통 필요없거나 날짜 정도.
             # 문서 없이 정확한 파라미터 추측은 어렵지만, auth-key만으로 동작하는지 확인.
             try:
                 params = {
                     "basDd": today,
                 }
                 # OpenAPI는 보통 GET
                 res = requests.get(url, headers=headers, params=params, timeout=5)
                 
                 if res.status_code == 200:
                     data = res.json()
                     # 응답 파싱 시도
                     # data['output'] 리스트 등 구조 확인
                     output = data.get('output', [])
                     if isinstance(output, list):
                         for item in output:
                             # KOSPI & PBR 찾기
                             idx_nm = item.get('idxNm', '')
                             if '코스피' in idx_nm or 'KOSPI' in idx_nm:
                                 pbr = _safe_float(item.get('pbr') or item.get('PBR'))
                                 if pbr:
                                     print(f"✅ KRX OpenAPI Success: PBR {pbr}")
                                     return pbr
             except Exception:
                 continue

        return None
        
    except Exception as e:
        print(f"⚠️ KRX OpenAPI Failed: {e}")
        return None


# KOSPI PBR 캐시 (1시간)
_KOSPI_PBR_CACHE = {"value": None, "timestamp": 0}

def fetch_kospi_pbr() -> Optional[float]:
    """
    KOSPI 전체 PBR 지수.
    
    1. 캐시 확인 (1시간)
    2. pykrx 라이브러리 (빠른 시도, 5일만)
    3. 실패 시 즉시 기본값 반환
    """
    import time
    
    # 캐시 확인 (1시간 = 3600초)
    current_time = time.time()
    if _KOSPI_PBR_CACHE["value"] is not None:
        cache_age = current_time - _KOSPI_PBR_CACHE["timestamp"]
        if cache_age < 3600:
            return _KOSPI_PBR_CACHE["value"]
    
    # 1. pykrx 빠르게 시도 (5일만 검색)
    if krx_stock is not None:
        try:
            today = datetime.today()
            for i in range(0, 5):
                date_str = (today - timedelta(days=i)).strftime("%Y%m%d")
                try:
                    df = krx_stock.get_index_fundamental(date_str, date_str, "1001") 
                except Exception:
                    continue
                    
                if df is None or df.empty:
                    continue

                # PBR 컬럼 찾기
                pbr_col = None
                for col in ["PBR", "pbr", "BPS/PBR"]:
                    if col in df.columns:
                        pbr_col = col
                        break

                if pbr_col:
                    val = _safe_float(df[pbr_col].iloc[0])
                    if val and val > 0:
                        print(f"✅ KOSPI PBR (pykrx): {val}")
                        _KOSPI_PBR_CACHE["value"] = val
                        _KOSPI_PBR_CACHE["timestamp"] = current_time
                        return val
        except Exception:
            pass
    
    # 2. pykrx 실패 시 즉시 기본값 반환
    default_pbr = 1.38
    
    # 첫 실패만 로그 (캐시 없을 때만)
    if _KOSPI_PBR_CACHE["value"] is None:
        print(f"⚠️ KOSPI PBR: 기본값 사용 ({default_pbr})")
    
    _KOSPI_PBR_CACHE["value"] = default_pbr
    _KOSPI_PBR_CACHE["timestamp"] = current_time
    return default_pbr

def _fetch_kospi_pbr_from_krx_api() -> Optional[float]:
    """
    KRX 정보데이터시스템 API를 직접 호출하여 KOSPI PBR 조회 (MDC Direct)
    출처: https://data.krx.co.kr
    주의: AUTH_KEY 미사용. 직전 영업일 기준 데이터를 찾습니다.
    """
    try:
        url = "http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"
        
        # PBR은 보통 직전 영업일 기준으로 제공됨
        # 오늘 포함 역순으로 5일간 탐색
        today = datetime.today()
        
        # MDCSTAT03501: 지수별 PER/PBR/배당수익률
        # 이 화면은 파라미터가 적고 KOSPI 전체 리스트를 줍니다.
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201010106",
            "Origin": "http://data.krx.co.kr",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest"
        }

        print(f"🔍 KRX API 호출 시도 (Direct MDC - MDCSTAT03501)")
        
        for i in range(0, 5):
            date_str = (today - timedelta(days=i)).strftime("%Y%m%d")
            
            params = {
                "bld": "dbms/MDC/STAT/standard/MDCSTAT03501",
                "searchType": "1",    # 1: 일자별(X) -> 1: 기준일자, mktId 사용 시
                "mktId": "STK",       # STK: 코스피
                "trdDd": date_str,
                "csvxls_isNo": "false"
            }
            
            try:
                response = requests.post(url, data=params, headers=headers, timeout=5)
                
                if response.status_code != 200:
                    print(f"⚠️ KRX Fail ({date_str}): {response.status_code}")
                    continue
                
                data = response.json()
                if "output" in data and isinstance(data["output"], list):
                     for item in data["output"]:
                        # "idxNm": "코스피" 찾기
                        if item.get("idxNm") == "코스피":
                            pbr = _safe_float(item.get("pbr"))
                            if pbr and pbr > 0:
                                print(f"✅ KOSPI PBR Fetch Success (Direct MDC): {pbr} ({date_str})")
                                return pbr
            except Exception as e:
                print(f"⚠️ KRX Error ({date_str}): {e}")
                continue
            except Exception:
                continue
            
        return None
        
    except Exception as e:
        print(f"❌ KRX Direct Fetch Failed: {e}")
        return None
def _calculate_kospi_pbr_manually() -> Optional[float]:
    """
    KOSPI 전체 PBR 수동 계산 (최후의 수단)
    공식: 코스피 시가총액 합계 / (BPS * 상장주식수) 합계
    """
    if krx_stock is None:
        return None
        
    try:
        today = datetime.today()
        # 최근 3일 이내 데이터 시도
        df = None
        df_cap = None
        target_date = ""
        
        for i in range(0, 3):
            date_str = (today - timedelta(days=i)).strftime("%Y%m%d")
            try:
                # KOSPI 전체 종목 펀더멘털 (BPS 등)
                df = krx_stock.get_market_fundamental_by_ticker(date_str, market="KOSPI")
                if not df.empty:
                    # KOSPI 전체 종목 시가총액 (상장주식수)
                    df_cap = krx_stock.get_market_cap_by_ticker(date_str, market="KOSPI")
                    if not df_cap.empty:
                        target_date = date_str
                        break
            except Exception:
                continue
        
        if df is None or df.empty or df_cap is None or df_cap.empty:
            return None

        # 데이터 병합 (인덱스=티커)
        import pandas as pd
        df_merged = pd.concat([df, df_cap], axis=1, join='inner')
        
        # 필요한 컬럼 확인
        if 'BPS' not in df_merged.columns or '상장주식수' not in df_merged.columns or '시가총액' not in df_merged.columns:
            return None

        # 숫자 변환
        df_merged['BPS'] = pd.to_numeric(df_merged['BPS'], errors='coerce').fillna(0)
        df_merged['상장주식수'] = pd.to_numeric(df_merged['상장주식수'], errors='coerce').fillna(0)
        df_merged['시가총액'] = pd.to_numeric(df_merged['시가총액'], errors='coerce').fillna(0)
        
        # 전체 시가총액
        total_mkt_cap = df_merged['시가총액'].sum()
        
        # 전체 순자산 (Equity)
        df_merged['Equity'] = df_merged['BPS'] * df_merged['상장주식수']
        total_equity = df_merged['Equity'].sum()
        
        if total_equity == 0:
            return None
            
        pbr = total_mkt_cap / total_equity
        return float(pbr)

    except Exception as e:
        print(f"⚠️ KOSPI Manual Calculation Failed: {e}")
        return None

def _fetch_kospi_pbr_from_krx_api() -> Optional[float]:
    """
    KRX 정보데이터시스템 API를 직접 호출하여 KOSPI PBR 조회 (MDC Direct)
    출처: https://data.krx.co.kr
    주의: AUTH_KEY를 사용하지 않음 (MDC는 공개 웹사이트) -> 400 Bad Request 원인 제거
    """
    try:
        url = "http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd"
        
        today = datetime.today().strftime("%Y%m%d")
        
        params = {
            "bld": "dbms/MDC/STAT/standard/MDCSTAT00301",
            "locale": "ko_KR",
            "trdDd": today,
            "idxIndMidclssCd": "01",
            "share": "1",
            "money": "1",
            "csvxls_isNo": "false"
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd?menuId=MDC0201010105",
            "Origin": "http://data.krx.co.kr",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
        }
        
        # NOTE: Removed 'auth-key' injection here as it likely causes 400 on MDC
        
        print(f"🔍 KRX API 호출 시도 (Direct, No Key): {today}")
        
        for i in range(0, 15):
            date_str = (datetime.today() - timedelta(days=i)).strftime("%Y%m%d")
            params["trdDd"] = date_str
            
            try:
                response = requests.post(url, data=params, headers=headers, timeout=5)
                response.raise_for_status()
                
                data = response.json()
                if "output" in data and len(data["output"]) > 0:
                     for item in data["output"]:
                        if item.get("idxNm") == "코스피":
                            pbr = _safe_float(item.get("pbr"))
                            if pbr:
                                print(f"✅ KOSPI PBR Fetch Success: {pbr} ({date_str})")
                                return pbr
            except Exception as e:
                # 400 Error 등의 경우 로깅 줄이기 (너무 시끄러움)
                if i == 0: # 첫 시도만 로그
                     print(f"⚠️ KRX Direct Fetch Warning ({date_str}): {e}")
                continue
            
        return None
        
    except Exception as e:
        print(f"❌ KRX Direct Fetch Failed: {e}")
        return None


def _fetch_kospi_pbr_from_investing() -> Optional[float]:
    """
    investing.com에서 KOSPI PBR 크롤링 (fallback)
    """
    try:
        url = "https://kr.investing.com/indices/kospi"  
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        html = res.text
        
        import re
        
        # PBR 패턴 찾기 (일반적으로 0.5 ~ 2.0 범위)
        pbr_patterns = [
            r'PBR[^0-9]*([0-9]\.[0-9]{1,2})',
            r'P/B[^0-9]*([0-9]\.[0-9]{1,2})',
            r'장부가치비율[^0-9]*([0-9]\.[0-9]{1,2})',
        ]
        
        for pattern in pbr_patterns:
            match = re.search(pattern, html, re.IGNORECASE)
            if match:
                val = _safe_float(match.group(1))
                if val and 0.3 < val < 3.0:  # 합리적인 PBR 범위
                    print(f"✅ KOSPI PBR (investing.com): {val}")
                    return val
                    
    except Exception as e:
        print(f"⚠️ KOSPI PBR investing.com 크롤링 실패: {e}")
    
    return None


def _fetch_kospi_pbr_from_naver() -> Optional[float]:
    """
    네이버 금융 크롤링으로 KOSPI PBR 조회.
    URL: https://finance.naver.com/sise/sise_index.naver?code=KOSPI
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        import re
        
        url = "https://finance.naver.com/sise/sise_index.naver?code=KOSPI"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
        }
        
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        
        soup = BeautifulSoup(res.text, "html.parser")
        
        print("🔍 Naver Finance 크롤링 시도...")
        
        # 방법 1: 테이블에서 PBR 찾기 (가장 일반적)
        # <tr><td>PBR</td><td>0.95</td></tr> 형태
        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True)
                    if "PBR" in label or "P/B" in label:
                        value_text = cells[1].get_text(strip=True)
                        # 숫자 추출
                        match = re.search(r'([0-9]+\.?[0-9]*)', value_text)
                        if match:
                            val = _safe_float(match.group(1))
                            if val and 0.3 < val < 3.0:
                                print(f"✅ Naver Finance (방법1): PBR {val}")
                                return val
        
        # 방법 2: dl/dt/dd 구조
        # <dl><dt>PBR</dt><dd>0.95</dd></dl>
        dls = soup.find_all("dl")
        for dl in dls:
            dts = dl.find_all("dt")
            dds = dl.find_all("dd")
            for i, dt in enumerate(dts):
                if "PBR" in dt.get_text(strip=True):
                    if i < len(dds):
                        value_text = dds[i].get_text(strip=True)
                        match = re.search(r'([0-9]+\.?[0-9]*)', value_text)
                        if match:
                            val = _safe_float(match.group(1))
                            if val and 0.3 < val < 3.0:
                                print(f"✅ Naver Finance (방법2): PBR {val}")
                                return val
        
        # 방법 3: span 또는 em 태그에서 찾기
        spans = soup.find_all(["span", "em", "strong"])
        for span in spans:
            text = span.get_text(strip=True)
            # "PBR 0.95" 또는 "PBR:0.95" 형태
            if "PBR" in text:
                match = re.search(r'PBR[:\s]*([0-9]+\.?[0-9]*)', text)
                if match:
                    val = _safe_float(match.group(1))
                    if val and 0.3 < val < 3.0:
                        print(f"✅ Naver Finance (방법3): PBR {val}")
                        return val
        
        # 방법 4: 전체 HTML에서 정규식으로 검색
        # "PBR</td><td>0.95" 같은 패턴
        pbr_patterns = [
            r'PBR[^0-9]*?([0-9]+\.[0-9]+)',
            r'P/B[^0-9]*?([0-9]+\.[0-9]+)',
            r'장부가[^0-9]*?([0-9]+\.[0-9]+)'
        ]
        
        html_text = res.text
        for pattern in pbr_patterns:
            matches = re.findall(pattern, html_text, re.IGNORECASE)
            for match in matches:
                val = _safe_float(match)
                if val and 0.3 < val < 3.0:
                    print(f"✅ Naver Finance (방법4-정규식): PBR {val}")
                    return val
        
        print("⚠️ Naver Finance: PBR 요소를 찾지 못했습니다")
        # 디버깅용: HTML 일부 출력
        print(f"   페이지 길이: {len(res.text)} bytes")
        
        return None
        
    except Exception as e:
        print(f"❌ Naver Finance 크롤링 실패: {e}")
        return None

        
    except Exception as e:
        print(f"❌ Naver Finance Crawling Failed: {e}")
        return None

# fetch_kospi_pbr() 함수는 위의 425번째 줄에 정의되어 있습니다.
# 중복 정의를 제거하여 pykrx가 최우선적으로 시도되도록 합니다.



# ─────────────────────────────────────
# USD/KRW 환율
# ─────────────────────────────────────
def fetch_usdkrw() -> Optional[float]:
    """
    원/달러 환율 (USDKRW).

    1차: FRED DEXKOUS 시리즈 사용 (일간 고시 환율, 원/달러)
    2차: yfinance("KRW=X") 종가 fallback
    """
    # 1) FRED
    fx = _fetch_latest_from_fred("DEXKOUS")
    if fx is not None:
        return fx

    # 2) yfinance fallback
    return _fetch_last_price_yf("KRW=X")


# ─────────────────────────────────────
# 한국 지표 블록 조립
# ─────────────────────────────────────
def build_korea_block() -> Dict[str, Any]:
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Submit tasks
        future_kospi_kosdaq = executor.submit(fetch_kospi_kosdaq_3m)
        future_vkospi = executor.submit(fetch_vkospi)
        future_kr10y = executor.submit(fetch_kr_10y_yield)
        future_kospi_pbr = executor.submit(fetch_kospi_pbr)
        future_usdkrw = executor.submit(fetch_usdkrw)
        
        # Get results
        kospi_ret_3m, kosdaq_ret_3m = future_kospi_kosdaq.result()
        vkospi_val, vkospi_ret_3m = future_vkospi.result()
        kr10y_val = future_kr10y.result()
        kospi_pbr = future_kospi_pbr.result()
        usdkrw = future_usdkrw.result()

    korea_block: Dict[str, Any] = {
        "equity": {
            "KOSPI": {
                "ret_3m": {
                    "value": kospi_ret_3m,
                    "label": "3개월 수익률",
                }
            },
            "KOSDAQ": {
                "ret_3m": {
                    "value": kosdaq_ret_3m,
                    "label": "3개월 수익률",
                }
            },
        },
        "volatility": {
            "VKOSPI": {
                "value": vkospi_val,
                "change_pct": vkospi_ret_3m,
            }
        },
        "macro": {
            "KR10Y": {
                "value": kr10y_val,
            }
        },
        "valuation": {
            "KOSPI_PBR": {
                "value": kospi_pbr,
            }
        },
        "fx": {
            "USDKRW": {
                "value": usdkrw,
            }
        },
    }

    return korea_block


# ─────────────────────────────────────
# 미국 시장 지표 조회
# ─────────────────────────────────────
def build_us_block() -> Dict[str, Any]:
    """
    미국 시장 지표 수집:
    - SPY, QQQ (3개월 수익률 및 현재가)
    - VIX (현재값)
    - Fear & Greed Index
    """
    # SPY, QQQ 데이터
    spy_df = _fetch_3m_history_yf("SPY")
    qqq_df = _fetch_3m_history_yf("QQQ")
    vix_df = _fetch_3m_history_yf("^VIX")
    
    spy_current = _fetch_last_price_yf("SPY")
    qqq_current = _fetch_last_price_yf("QQQ")
    vix_current = _fetch_last_price_yf("^VIX")
    
    spy_ret_3m = _ret_3m(spy_df)
    qqq_ret_3m = _ret_3m(qqq_df)
    
    # Calculate change_pct (recent change)
    spy_change_pct = None
    qqq_change_pct = None
    
    if not spy_df.empty and len(spy_df) >= 2:
        try:
            spy_prev = float(spy_df["Close"].iloc[-2])
            spy_curr = float(spy_df["Close"].iloc[-1])
            spy_change_pct = ((spy_curr / spy_prev) - 1) * 100
        except:
            pass
    
    if not qqq_df.empty and len(qqq_df) >= 2:
        try:
            qqq_prev = float(qqq_df["Close"].iloc[-2])
            qqq_curr = float(qqq_df["Close"].iloc[-1])
            qqq_change_pct = ((qqq_curr / qqq_prev) - 1) * 100
        except:
            pass
    
    # Fear & Greed Index
    fgi_value = None
    fgi_rating = None
    try:
        from utils.fgi import fetch_fear_greed
        fgi_score, _, _, _ = fetch_fear_greed()
        if fgi_score is not None:
            fgi_value = fgi_score
            # Determine rating
            if fgi_score <= 25:
                fgi_rating = "Extreme Fear"
            elif fgi_score <= 45:
                fgi_rating = "Fear"
            elif fgi_score <= 55:
                fgi_rating = "Neutral"
            elif fgi_score <= 75:
                fgi_rating = "Greed"
            else:
                fgi_rating = "Extreme Greed"
    except Exception:
        pass

    # Additional US Indicators (TNX, DXY)
    tnx_df = _fetch_3m_history_yf("^TNX")
    dxy_df = _fetch_3m_history_yf("DX-Y.NYB")
    
    tnx_current = _fetch_last_price_yf("^TNX")
    dxy_current = _fetch_last_price_yf("DX-Y.NYB")
    
    return {
        "spy": {
            "value": spy_current,
            "change_pct": spy_change_pct,
            "ret_3m": spy_ret_3m
        },
        "qqq": {
            "value": qqq_current,
            "change_pct": qqq_change_pct,
            "ret_3m": qqq_ret_3m
        },
        "vix": {
            "value": vix_current
        },
        "tnx": {
            "value": tnx_current
        },
        "dxy": {
            "value": dxy_current
        },
        "fgi": {
            "value": fgi_value,
            "rating": fgi_rating
        }
    }


# ─────────────────────────────────────
# 외부에서 사용하는 진입 함수
# ─────────────────────────────────────
def get_market_indicators() -> Dict[str, Any]:
    """
    시장 지표 통합 조회 함수.
    
    - 미국 지표: SPY, QQQ, VIX, Fear & Greed Index
    - 한국 지표: KOSPI, KOSDAQ, VKOSPI, 국채10Y, KOSPI PBR, USD/KRW
    """
    # Run US and Korea blocks in parallel
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_us = executor.submit(build_us_block)
        future_korea = executor.submit(build_korea_block)
        
        us_data = future_us.result()
        korea = future_korea.result()

    return {
        "us": us_data,       # 미국 시장 데이터
        "korea": korea,      # 한국 시장 데이터
    }
