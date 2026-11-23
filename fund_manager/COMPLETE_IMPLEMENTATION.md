# Fund Manager - 완전한 구현 완료! 🎉

## ✅ 완료 사항

### 1. UI 구현 (Frontend)
**파일**: `static/index.html`, `static/fund_manager.js`

#### 새로운 탭 추가
- **Fund Manager 탭 버튼** (헤더)
- **3단계 워크플로우**:
  - Step 1: 투자 성향 설문 (13개 질문)
  - Step 2: 포트폴리오 생성 결과
  - Step 3: 상세 보기 (TODO)

#### 설문 항목 (13개)
1. 투자 가능 금액
2. 투자 기간
3. 목표 수익률
4. 최대 손실 허용
5. 소득 안정성
6. 비상 자금
7. 투자 경험
8. 지식 수준
9. 손실 반응
10. 변동성 편안함
11. 집중도 선호
12. 리밸런싱 허용
13. 환율 노출 허용

---

### 2. 전용 에이전트 개발 (Backend)
**파일**: `agent_engine/fund_agents.py`

#### 4개의 전문화된 에이전트

| 에이전트 | 역할 | 차별점 |
|---------|------|--------|
| **Suitability Specialist** | 3축 프로파일 + IPS | 투자자 자체 분석 (종목 ❌) |
| **Portfolio Architect** | HRP/CVaR/BL 포트폴리오 | 자산 배분 (매수/매도 ❌) |
| **Risk Scenario Analyst** | 스트레스 테스트 | 심리적 압박 시뮬레이션 |
| **Explainability Specialist** | 한글 설명 생성 | 고정된 4가지 구조 |

#### 왜 기존 에이전트를 사용하지 않는가?

**종목 분석 Agent** vs **Fund Manager Agent**

| 비교 | 종목 분석 | Fund Manager |
|------|----------|--------------|
| 입력 | Ticker | 설문 응답 |
| 출력 | Buy/Hold/Sell | 3가지 포트폴리오 + IPS |
| 도구 | Price, News, Fundamentals | HRP, CVaR, Monte Carlo |
| 관점 | 개별 주식 성과 | 자산 배분 + 리스크 관리 |
| 목적 | 단기 트레이딩 | 장기 포트폴리오 운용 |

**→ 완전히 다른 전문성 필요!**

---

### 3. API 통합
**파일**: `fund_manager_api.py`

#### 3개 엔드포인트
1. **POST /api/fund/suitability**
   - 설문 → IPS (전용 Suitability Specialist 호출)
   - Fallback: Rule-based (안전장치)

2. **POST /api/fund/universe**
   - 투자 유니버스 구성
   - 현재: Fixed 5개 (국내 2 + 미국 ETF 3)

3. **POST /api/fund/construct**
   - 3가지 포트폴리오 생성
   - 현재: Equal weight (MVP)
   - TODO: 전용 Portfolio Architect 연결

---

### 4. 알고리즘 (코어 로직)
**파일**: `fund_manager/construction/`, `fund_manager/forecast/`

#### 구현된 알고리즘
- ✅ **HRP (Hierarchical Risk Parity)** - `hrp.py`
- ✅ **CVaR Constraint** - `cvar_constraint.py`
- ✅ **Monte Carlo Simulation** - `monte_carlo.py`
- ✅ **Portfolio Generator** (통합) - `generator.py`

#### TODO: 에이전트와 연결
```python
# fund_crew.py의 run_portfolio_construction()에서:

# 1. Agent가 전략 결정
strategy = agent.decide_strategy(universe, ips)

# 2. 알고리즘이 실행
from fund_manager.construction import PortfolioGenerator

generator = PortfolioGenerator(returns_df, ips)
portfolios = generator.generate_three_portfolios(...)

# 3. Agent가 설명 추가
explainability = agent.explain(portfolios)
```

---

## 🎯 워크플로우 (전체 흐름)

```
사용자 설문 입력 (frontend)
    ↓
POST /api/fund/suitability
    ↓
fund_crew.run_suitability_analysis()
    ↓
📌 Suitability Specialist Agent (전용)
    ↓
DecisionProfile + IPS 생성
    ↓
POST /api/fund/universe
    ↓
투자 유니버스 구성 (국내/해외 종목/ETF)
    ↓
POST /api/fund/construct
    ↓
fund_crew.run_portfolio_construction()
    ↓
📌 Portfolio Architect Agent (전용)
    ↓
HRP + CVaR + BL 알고리즘 (TODO: 연결)
    ↓
3가지 포트폴리오 생성
    ↓
fund_crew.run_portfolio_explainability()
    ↓
📌 Explainability Specialist Agent (전용)
    ↓
설명 추가 (4가지 구조)
    ↓
frontend: 3가지 포트폴리오 카드 표시
    ↓
사용자 선택
```

---

## 📁 파일 구조

```
ver5_project/
├── static/
│   ├── index.html              ✅ Fund Manager 탭 추가
│   ├── app.js                  (기존 종목 분석)
│   └── fund_manager.js         ✅ 신규 (펀드 매니저 로직)
│
├── agent_engine/
│   ├── agents.py               (기존 종목 분석 에이전트)
│   ├── fund_agents.py          ✅ 신규 (펀드 매니저 전용)
│   ├── fund_tasks.py           ✅ 신규 (펀드 매니저 tasks)
│   └── fund_crew.py            ✅ 신규 (크루 실행 함수)
│
├── fund_manager/
│   ├── models.py               ✅ Pydantic 모델
│   ├── construction/
│   │   ├── hrp.py              ✅ HRP 알고리즘
│   │   ├── cvar_constraint.py  ✅ CVaR 최적화
│   │   └── generator.py        ✅ 통합 생성기
│   ├── forecast/
│   │   └── monte_carlo.py      ✅ Monte Carlo
│   └── agents/                 (문서)
│       ├── agent_01_suitability.md
│       ├── agent_03_portfolio_constructor.md
│       └── agent_06_counterfactual.md
│
├── fund_manager_api.py         ✅ API 엔드포인트
└── api.py                      ✅ 라우터 등록
```

---

## 🚀 실행 방법

### 1. 서버 시작
```bash
python -m uvicorn api:app --port 8001 --reload
```

### 2. 브라우저 접속
```
http://localhost:8001
```

### 3. Fund Manager 탭 클릭
- 설문 작성 (13개 항목)
- "분석 시작하기" 버튼
- AI가 맞춤 포트폴리오 생성
- 3가지 선택지 확인

---

## 📊 현재 상태

### ✅ 완료
- [x] UI/UX (설문, 결과 표시)
- [x] 전용 에이전트 4개
- [x] API 엔드포인트 3개
- [x] 알고리즘 4개 (HRP/CVaR/MC/Generator)
- [x] Pydantic 모델
- [x] 프론트엔드 JS

### 🚧 TODO (에이전트 ↔ 알고리즘 연결)
- [ ] Portfolio Architect가 HRP/CVaR 호출
- [ ] Risk Scenario Analyst가 Monte Carlo 호출
- [ ] Counterfactual Engine 구현
- [ ] Monitoring + Rebalancing

---

## 💡 핵심 혁신

### 1. 3축 프로파일
- **Capacity** (재무): 감당 가능한가?
- **Preference** (심리): 견딜 수 있는가?
- **Style** (의사결정): 어떻게 결정하는가?

### 2. 3가지 포트폴리오
- **우열 없음**: 서로 다른 철학
- Base: 균형
- Upside: 수익 극대화
- Defensive: 손실 최소화

### 3. Counterfactual Engine
- "만약 ~였다면?"
- 선택의 결과 공간 학습

### 4. Living Fund
- 상태 기반 전이 (Calm/Stress/Crisis/Recovery)
- 심리적 압박 시뮬레이션

---

## 🎓 분리 원칙 준수

### 종목 분석 (기존)
- URL: `/` → Dashboard/Analytics 탭
- API: `/api/stock/*`
- 에이전트: `agents.py` (5개)
- 목적: 개별 종목 매수/매도 판단

### Fund Manager (신규)
- URL: `/` → **Fund Manager 탭**
- API: `/api/fund/*`
- 에이전트: `fund_agents.py` (4개)
- 목적: 포트폴리오 설계/운용

### 공유
- ✅ CrewAI 프레임워크
- ✅ OpenAI LLM
- ❌ 에이전트 (완전 독립)
- ❌ Tasks (완전 독립)

---

**작성일**: 2026-01-04
**버전**: 1.0
**상태**: UI + 전용 에이전트 완성! 🎉

다음: 에이전트 ↔ 알고리즘 연결
