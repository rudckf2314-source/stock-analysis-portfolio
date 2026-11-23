# FDGE Fund Manager - Agent System 설계

## 개요

펀드 매니저 기능은 **10개의 전문화된 AI 에이전트**가 협력하여 작동합니다.
각 에이전트는 특정 도메인의 전문가 역할을 수행하며, CrewAI 프레임워크로 orchestration됩니다.

## 핵심 원칙

1. **책임 분리**: 각 에이전트는 단일 책임만 수행
2. **명확한 입출력**: 구조화된 JSON 입출력
3. **설명 가능성**: 모든 결정에 근거 제시
4. **일관된 톤**: 전문가이지만 친절한 조언자
5. **규제 준수**: "추천"이 아닌 "분석 제공"

## 에이전트 구성

### Phase 1: 프로파일링
1. **Suitability Agent** - 설문 → 3축 프로파일 + IPS

### Phase 2: 유니버스
2. **Universe Curator Agent** - 투자 대상 선정

### Phase 3: 포트폴리오 생성
3. **Portfolio Constructor Agent** - HRP/CVaR/BL 실행
4. **Scenario Analyst Agent** - 시나리오별 손익
5. **Forecast Agent** - 성과 예측 + 확률

### Phase 4: 의사결정 지원
6. **Counterfactual Agent** - "만약 ~라면" 분석
7. **Explainability Agent** - 근거 생성

### Phase 5: 지속 운용
8. **Monitoring Agent** - 상태 감시
9. **Rebalancer Agent** - 리밸런싱 제안

### Phase 6: 최종 승인
10. **Head PM Agent** - 최종 검토 및 요약

## 에이전트별 상세 문서

각 에이전트의 상세 프롬프트는 별도 파일로 관리:

1. `agent_01_suitability.md` - Suitability Agent
2. `agent_02_universe_curator.md` - Universe Curator Agent
3. `agent_03_portfolio_constructor.md` - Portfolio Constructor Agent
4. `agent_04_scenario_analyst.md` - Scenario Analyst Agent
5. `agent_05_forecast.md` - Forecast Agent
6. `agent_06_counterfactual.md` - Counterfactual Agent
7. `agent_07_monitoring.md` - Monitoring Agent
8. `agent_08_rebalancer.md` - Rebalancer Agent
9. `agent_09_explainability.md` - Explainability Agent
10. `agent_10_head_pm.md` - Head PM Agent

## 공통 프롬프트 템플릿

모든 에이전트는 다음 구조를 따릅니다:

```
[ROLE]
당신은 {역할 이름}입니다.

[CONTEXT]
{배경 정보}

[TASK]
{수행할 작업}

[CONSTRAINTS]
- {제약 조건 1}
- {제약 조건 2}

[OUTPUT FORMAT]
{출력 형식 - 반드시 JSON}

[TONE]
- 전문가이지만 친절한 조언자
- "추천"이 아닌 "분석 제공"
- 불확실성을 솔직하게 표현
```

## CrewAI 통합

### Agent 정의
```python
from crewai import Agent

suitability_agent = Agent(
    role="투자 적합성 분석 전문가",
    goal="사용자 설문을 분석하여 3축 투자 프로파일과 IPS를 생성",
    backstory="15년 경력의 자산관리 전문가. 수천 명의 투자자 프로파일을 분석한 경험.",
    verbose=True,
    allow_delegation=False,
    llm=llm_gpt4o
)
```

### Task 정의
```python
from crewai import Task

suitability_task = Task(
    description="""
    사용자 설문 응답을 분석하여 다음을 생성하세요:
    1. Risk Capacity (재무적 감당력)
    2. Risk Preference (심리적 감내도)
    3. Decision Style (의사결정 스타일)
    4. IPS (Investment Policy Statement)
    
    입력: {survey_responses}
    """,
    expected_output="""
    JSON 형식:
    {
        "decision_profile": {...},
        "ips": {...},
        "profile_summary": "..."
    }
    """,
    agent=suitability_agent
)
```

## 에이전트 간 데이터 흐름

```
설문 응답
    ↓
[Suitability] → DecisionProfile + IPS
    ↓
[Universe Curator] → 투자 유니버스 (20-30개)
    ↓
[Portfolio Constructor] → 3가지 포트폴리오
    ↓
[Scenario Analyst] → 시나리오별 분석
    ↓
[Forecast] → 성과 분포 + 확률
    ↓
[Counterfactual] → 대안 시뮬레이션
    ↓
[Explainability] → 설명 생성
    ↓
[Head PM] → 최종 검토 + 요약
    ↓
사용자에게 3가지 선택지 제시

(지속 운용)
[Monitoring] → 상태 감시 → [Rebalancer] → 제안
```

## 다음 단계

1. ✅ 전체 에이전트 시스템 개요
2. ⏭️ 각 에이전트별 상세 프롬프트 작성
3. ⏭️ CrewAI 코드 구현
4. ⏭️ 테스트 시나리오 작성

---

**작성일**: 2026-01-04
**버전**: 1.0
