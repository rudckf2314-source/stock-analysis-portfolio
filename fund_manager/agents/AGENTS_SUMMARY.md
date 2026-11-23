# FDGE Fund Manager - Agent Prompts 요약

## 완성된 상세 프롬프트 (3개)

### ✅ Agent 01: Suitability Agent
**파일**: `agent_01_suitability.md`
**역할**: 설문 → 3축 프로파일 + IPS
**핵심**: 재무 능력 ≠ 심리 선호 구분

### ✅ Agent 03: Portfolio Constructor
**파일**: `agent_03_portfolio_constructor.md`
**역할**: HRP + CVaR + BL → 3가지 포트폴리오
**핵심**: Base/Upside/Defensive는 우열이 아닌 철학 차이

### ✅ Agent 06: Counterfactual Agent
**파일**: `agent_06_counterfactual.md`
**역할**: "만약 ~였다면" 시뮬레이션
**핵심**: 선택의 결과 공간 학습

---

## 나머지 에이전트 프롬프트 (간략 버전)

### 🔹 Agent 02: Universe Curator
**역할**: 투자 유니버스 선정
**입력**: DecisionProfile + IPS
**출력**: 20-30개 종목/ETF 리스트
**핵심 로직**:
```
IF risk_level >= 4:
    include: 성장주, 테마 ETF, 레버리지 (소량)
ELIF risk_level <= 2:
    include: 대형주, 지수 ETF, 채권 ETF
ELSE:
    include: 블루칩 + 지수 ETF + 일부 성장주
```

---

### 🔹 Agent 04: Scenario Analyst
**역할**: 시나리오별 손익 분석
**시나리오**:
1. 금리 급등 (+1.5%p)
2. 경기 침체 (GDP -2%)
3. 섹터 붕괴 (반도체 -30%)
4. 달러 급락 (원/달러 -15%)

**출력**: 각 시나리오에서 포트폴리오 손익 %

---

### 🔹 Agent 05: Forecast Agent
**역할**: 몬테카를로 시뮬레이션 + 목표 달성 확률
**입력**: Portfolio + 목표 금액/기간
**출력**:
- 분위수 (p10/p50/p90)
- 목표 달성 확률
- 부족액 예상 (shortfall)

**핵심 공식**:
```python
goal_achievement_prob = (
    시뮬 10,000회 중 목표 달성 횟수 / 10,000
)
```

---

### 🔹 Agent 07: Monitoring Agent
**역할**: Living Fund 상태 판단
**상태**: Calm / Stress / Crisis / Recovery
**전이 조건**:
```
Calm → Stress:
    volatility > target_vol * 1.5
    OR consecutive_loss_days > threshold

Stress → Crisis:
    estimated_mdd > max_tolerable_loss * 1.2

Crisis → Recovery:
    drawdown_recovery_rate > 0.5
    AND volatility_normalized
```

---

### 🔹 Agent 08: Rebalancer Agent
**역할**: 리밸런싱 제안 생성
**트리거**:
1. 비중 이탈 (±5% 밴드 초과)
2. 상태 전이 발생
3. 월간 정기 점검

**출력**:
- 매수/매도 리스트
- 예상 거래비용
- 거래 이유

**중요**: 제안만, 실행 안 함

---

### 🔹 Agent 09: Explainability Agent
**역할**: 설명 생성 (고정 구조)
**출력 구조**:
```json
{
  "why_this_portfolio": [...],
  "main_risk_factors": [...],
  "why_not_others": [...],
  "what_to_watch": [...]
}
```

**톤**: 전문가이지만 친절, 판단 안 함

---

### 🔹 Agent 10: Head PM Agent
**역할**: 최종 검토 + 요약
**책임**:
1. 모든 에이전트 결과 통합
2. 일관성 검증
3. 한 페이지 요약 생성

**출력**:
- Executive Summary
- 3가지 포트폴리오 비교표
- Top 3 Key Insights
- Next Steps

---

## 구현 우선순위

### Phase 1 (MVP) - 필수 3개
1. ✅ Suitability Agent
2. ✅ Portfolio Constructor
3. ✅ Explainability Agent (간단 버전)

### Phase 2 - 핵심 기능
4. Universe Curator
5. Forecast Agent
6. Counterfactual Agent

### Phase 3 - 고급 기능
7. Scenario Analyst
8. Monitoring Agent
9. Rebalancer Agent
10. Head PM Agent

---

## CrewAI Crew 구성

```python
from crewai import Crew

fund_manager_crew = Crew(
    agents=[
        suitability_agent,
        universe_curator,
        portfolio_constructor,
        scenario_analyst,
        forecast_agent,
        counterfactual_agent,
        explainability_agent,
        head_pm_agent
    ],
    tasks=[
        suitability_task,
        universe_task,
        construction_task,
        scenario_task,
        forecast_task,
        counterfactual_task,
        explainability_task,
        head_pm_task
    ],
    verbose=True,
    process="sequential"  # 순차 실행
)

# 실행
result = fund_manager_crew.kickoff(inputs={
    "survey_responses": {...}
})
```

---

## 다음 단계

1. ✅ 핵심 3개 에이전트 상세 프롬프트
2. ✅ 나머지 7개 에이전트 간략 프롬프트
3. ⏭️ Pydantic 데이터 모델 정의
4. ⏭️ 알고리즘 코어 구현 (HRP/CVaR)
5. ⏭️ CrewAI 통합 코드
6. ⏭️ API 엔드포인트 구현

---

**작성일**: 2026-01-04
**버전**: 1.0

## 필요한 추가 리소스

### 라이브러리
```bash
pip install crewai
pip install crewai-tools
pip install scipy  # HRP용
pip install cvxpy  # CVaR 최적화용
```

### 데이터
- 과거 수익률 데이터 (yfinance)
- 상관계수 행렬
- 섹터/테마 분류
- ETF 구성 정보

### 설정
- OpenAI API (GPT-4o)
- DeepL API (번역, 선택)
