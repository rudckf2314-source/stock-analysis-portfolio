# utils/search.py
# 번역 + 심볼 검색 모듈

import re
import requests
from utils.config import client, OPENAI_API_KEY, OPENAI_CHAT_MODEL
from utils.finance_data import fetch_price_history  # 앞으로 국내/미국 공통으로 쓸 수 있음
from utils.kis_api import search_korean_stocks

# 주요 미국 주식 한글 매핑 (AI 없이 즉시 변환)
KOREAN_TO_SYMBOL = {
    # 대형 기술주 (M7)
    "애플": "AAPL", "테슬라": "TSLA", "엔비디아": "NVDA", "마이크로소프트": "MSFT", "마소": "MSFT",
    "아마존": "AMZN", "구글": "GOOGL", "알파벳": "GOOGL", "메타": "META", "페이스북": "META",
    
    # 반도체
    "에이엠디": "AMD", "티에스엠씨": "TSM", "인텔": "INTC", "마이크론": "MU", "퀄컴": "QCOM", "브로드컴": "AVGO",
    
    # ETF
    "에스앤피": "SPY", "나스닥": "QQQ", "반도체etf": "SOXX", "배당etf": "SCHD",
    
    # 소비재/기타
    "스타벅스": "SBUX", "코카콜라": "KO", "펩시": "PEP", "맥도날드": "MCD", "넷플릭스": "NFLX",
    "나이키": "NKE", "디즈니": "DIS", "팔란티어": "PLTR", "아이온큐": "IONQ", "리비안": "RIVN", "루시드": "LCID"
}

def translate_to_english(text: str) -> str:
    """
    한국어로 입력된 미국/해외 종목 검색어를 영어 티커로 변환.
    속도를 위해 AI 대신 정적 매핑(Dictionary) 사용.
    """
    cleaned = text.replace(" ", "").strip()
    
    # 1. 매핑된 종목이면 즉시 영어 티커 반환
    if cleaned in KOREAN_TO_SYMBOL:
        print(f"[Map] '{text}' -> '{KOREAN_TO_SYMBOL[cleaned]}'")
        return KOREAN_TO_SYMBOL[cleaned]
        
    # 2. 매핑 없으면 원본 반환 (Yahoo가 알아서 처리하길 기대)
    return text


def _contains_korean(text: str) -> bool:
    """한글 포함 여부 간단 체크."""
    return bool(re.search("[가-힣]", text))


def search_symbols(query: str, quotes_count: int = 10):
    """
    통합 종목 검색:
    - 국내: KIS + pykrx 기반 search_korean_stocks()
    - 해외: Yahoo Finance 검색 API
    반환: (results, translated_query)
      results: [{symbol, name, exchange, region}, ...]
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    translated = translate_to_english(query)
    results = []

    # 1) 국내 종목 검색 (한글/숫자 코드 위주)
    try:
        kr_results = search_korean_stocks(query, limit=quotes_count)
        results.extend(kr_results)
    except Exception:
        # KIS/pykrx 쪽에서 에러가 나더라도 미국 검색은 계속 진행
        pass

    # 2) 미국/해외 종목 – Yahoo Finance
    for q in [query, translated]:
        if not q:
            continue
        url = "https://query1.finance.yahoo.com/v1/finance/search"
        params = {
            "q": q,
            "quotesCount": quotes_count,
            "newsCount": 0,
            "lang": "en-US",
            "region": "US",
        }
        try:
            r = requests.get(url, params=params, headers=headers, timeout=10)
            r.raise_for_status()
            quotes = r.json().get("quotes", [])
            for item in quotes:
                results.append(
                    {
                        "symbol": item.get("symbol"),
                        "name": item.get("shortname") or item.get("longname"),
                        "exchange": item.get("exchDisp"),
                        "region": item.get("region"),
                    }
                )
        except Exception:
            continue

    # 3) 심볼 + region 기준으로 중복 제거
    seen = set()
    deduped = []
    for r in results:
        key = (r.get("symbol"), r.get("region"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)

    return deduped, translated
