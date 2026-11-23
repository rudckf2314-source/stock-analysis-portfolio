# Fund Manager API 구현 완료

## ✅ 구현 완료 항목

### 1. Pydantic 모델
**파일**: `fund_manager/models.py`

**Request 모델**:
- `SuitabilityRequest` - 설문 응답
- `UniverseRequest` - 유니버스 구성 요청
- `ConstructionRequest` - 포트폴리오 생성 요청

**Response 모델**:
- `SuitabilityResponse` - DecisionProfile + IPS
- `UniverseResponse` - 종목/ETF 리스트
- `ConstructionResponse` - 3가지 포트폴리오

---

### 2. API 엔드포인트 (3개)
**파일**: `fund_manager_api.py`

#### POST /api/fund/suitability
**설문 분석 → 프로파일 생성**

**Request**:
```json
{
  "investable_amount": 50000000,
  "investment_period_months": 60,
  "max_loss_tolerance_pct": 20,
  "target_annual_return_pct": 10,
  "income_stability": "stable",
  "emergency_fund_months": 12,
  ...
}
```

**Response**:
```json
{
  "decision_profile": {
    "risk_capacity": {...},
    "risk_preference": {...},
    "decision_style": {...}
  },
  "ips": {
    "risk_level": 3,
    "target_vol": 0.15,
    "max_drawdown_target": 0.20,
    "cvar_limit_95": 0.12,
    ...
  },
  "profile_summary": "위험 Level 3 - 균형잡힌 투자자",
  "key_insights": [...]
}
```

**현재 구현**: Rule-based MVP
**TODO**: Suitability Agent (CrewAI) 연결

---

#### POST /api/fund/universe
**투자 유니버스 구성**

**Request**:
```json
{
  "region_preference": {
    "domestic_pct": 50,
    "overseas_pct": 50
  },
  "asset_types": ["stock", "etf"],
  ...
}
```

**Response**:
```json
{
  "universe": [
    {
      "ticker": "005930.KS",
      "name": "삼성전자",
      "asset_type": "stock",
      "region": "KR",
      ...
    },
    ...
  ],
  "stats": {
    "total_count": 5,
    "domestic_count": 2,
    "overseas_count": 3,
    ...
  }
}
```

**현재 구현**: Fixed universe (5개 자산)
**TODO**: Dynamic universe based on criteria

---

#### POST /api/fund/construct
**3가지 포트폴리오 생성**

**Request**:
```json
{
  "universe": [...],
  "initial_capital": 50000000,
  "investment_goal": {
    "target_amount": 75000000,
    "target_date": "2031-01-01"
  },
  "user_views": [...]
}
```

**Response**:
```json
{
  "portfolios": [
    {
      "name": "Base",
      "description": "설문 조건을 가장 충실히 반영한 균형 포트폴리오",
      "holdings": [...],
      "forecast": {
        "return_p50": 0.08,
        "goal_achievement_prob": 0.65,
        ...
      },
      "explainability": {...}
    },
    {
      "name": "Upside-Seeking",
      ...
    },
    {
      "name": "Downside-Defensive",
      ...
    }
  ]
}
```

**현재 구현**: Equal weight MVP
**TODO**: PortfolioGenerator (HRP + CVaR) 연결

---

## 🔗 API 등록

**파일**: `api.py` (line 933-935)

```python
from fund_manager_api import router as fund_manager_router
app.include_router(fund_manager_router)
```

FastAPI의 APIRouter를 사용하여 메인 앱에 등록 완료.

---

## 🧪 테스트 방법

### 1. 서버 실행
```bash
python -m uvicorn api:app --host 0.0.0.0 --port 8001 --reload
```

### 2. Swagger UI 접속
```
http://localhost:8001/docs
```

### 3. API 테스트
#### Step 1: 설문 분석
```bash
curl -X POST "http://localhost:8001/api/fund/suitability" \
  -H "Content-Type: application/json" \
  -d '{
    "investable_amount": 50000000,
    "investment_period_months": 60,
    "max_loss_tolerance_pct": 20,
    "target_annual_return_pct": 10,
    "income_stability": "stable",
    "emergency_fund_months": 12,
    "investment_experience": "intermediate",
    "knowledge_level": "medium",
    "loss_reaction": "concern",
    "volatility_comfort": "medium",
    "concentration_preference": "diversified",
    "rebalance_tolerance": "moderate",
    "fx_exposure_tolerance": "medium"
  }'
```

#### Step 2: 유니버스 구성
```bash
curl -X POST "http://localhost:8001/api/fund/universe" \
  -H "Content-Type: application/json" \
  -d '{
    "region_preference": {
      "domestic_pct": 50,
      "overseas_pct": 50
    },
    "asset_types": ["stock", "etf"]
  }'
```

#### Step 3: 포트폴리오 생성
```bash
curl -X POST "http://localhost:8001/api/fund/construct" \
  -H "Content-Type: application/json" \
  -d '{
    "universe": [...],  // from step 2
    "initial_capital": 50000000,
    "investment_goal": {
      "target_amount": 75000000,
      "target_date": "2031-01-01"
    },
    "user_views": []
  }'
```

---

## 📊 현재 상태

### ✅ 완료
- [x] Pydantic 모델 정의
- [x] 3개 API 엔드포인트 (MVP 버전)
- [x] FastAPI 라우터 등록
- [x] Swagger UI 자동 생성

### 🚧 진행 중 (MVP → Full)
- [ ] Suitability: Rule-based → CrewAI Agent
- [ ] Universe: Fixed 5개 → Dynamic selection
- [ ] Construction: Equal weight → HRP + CVaR

### ⏭️ 다음 단계
1. **알고리즘 연결**: PortfolioGenerator를 API에 통합
2. **에이전트 연결**: CrewAI Suitability Agent
3. **프론트엔드**: 설문 UI, 포트폴리오 비교 화면
4. **추가 API**: Forecast, Counterfactual, Monitoring

---

## 🎯 MVP vs Full 비교

| 기능 | MVP (현재) | Full (목표) |
|------|-----------|------------|
| **Suitability** | Rule-based | CrewAI Agent + 3축 분석 |
| **Universe** | Fixed 5개 자산 | Dynamic 20-30개 |
| **Construction** | Equal weight | HRP + CVaR + BL |
| **Forecast** | 고정값 | Monte Carlo 10K runs |
| **Counterfactual** | N/A | 파라미터 변경 시뮬 |

---

## 🔑 필요 액션

### 즉시 실행 가능
```bash
# 1. 서버 실행
python -m uvicorn api:app --port 8001 --reload

# 2. Swagger UI 확인
open http://localhost:8001/docs

# 3. API 테스트
# (위의 curl 명령어 사용)
```

### 다음 통합
```python
# fund_manager_api.py의 construct_portfolios에서:

# 현재:
n_assets = len(universe)
base_weight = 1.0 / n_assets

# 변경 후:
from fund_manager.construction import PortfolioGenerator, IPS

generator = PortfolioGenerator(returns_df, ips)
portfolios = generator.generate_three_portfolios(...)
```

---

**작성일**: 2026-01-04
**버전**: MVP 1.0
**상태**: API 엔드포인트 구현 완료 ✅
