# Fund Manager - 핵심 알고리즘 구현 완료

## ✅ 구현 완료 항목

### 1. HRP (Hierarchical Risk Parity)
**파일**: `fund_manager/construction/hrp.py`
**역할**: 상관구조 기반 클러스터링으로 자연스러운 분산 달성

**알고리즘**:
1. 상관계수 → 거리행렬 변환
2. 계층적 클러스터링 (Hierarchical Clustering)
3. 준대각화 (Quasi-Diagonalization)
4. 재귀적 이분할 (Recursive Bisection)

**장점**:
- 표본오차에 강함
- 과최적화 방지
- 직관적이고 안정적

---

### 2. CVaR Constraint Optimization
**파일**: `fund_manager/construction/cvar_constraint.py`
**역할**: 꼬리위험(Tail Risk) 제한

**공식**:
```
CVaR_α(X) = E[X | X >= VaR_α(X)]
```

**예시**:
- CVaR_95 = 0.10 의미
- 최악의 5% 시나리오에서 평균 손실 ≤ 10%

**구현**:
- CVXPY를 사용한 Convex Optimization
- HRP 비중을 초기값으로, CVaR 제약 하에 최적화

---

### 3. Monte Carlo Simulation
**파일**: `fund_manager/forecast/monte_carlo.py`
**역할**: 미래 성과 확률 분포 예측

**출력**:
- 분위수 (p5, p10, p25, p50, p75, p90, p95)
- 목표 달성 확률
- 예상 부족액 (Shortfall)

**파라미터**:
- `n_simulations`: 10,000 (기본값)
- 일별 수익률 시뮬레이션 → 복리 계산

---

### 4. Portfolio Generator (통합)
**파일**: `fund_manager/construction/generator.py`
**역할**: 3가지 포트폴리오 생성 엔진

**통합 플로우**:
```
HRP
  ↓
CVaR 제약
  ↓
(Base / Upside / Defensive 전략 적용)
  ↓
Monte Carlo 예측
  ↓
3가지 Portfolio 출력
```

**3가지 포트폴리오**:
1. **Base**: 균형잡힌 기본 포트폴리오
2. **Upside-Seeking**: 고수익 자산 비중↑
3. **Downside-Defensive**: 안정 자산 비중↑

---

## 📁 파일 구조

```
fund_manager/
├── __init__.py
├── construction/
│   ├── __init__.py
│   ├── hrp.py                    # HRP 알고리즘
│   ├── cvar_constraint.py        # CVaR 최적화
│   └── generator.py              # 통합 생성 엔진
├── forecast/
│   ├── __init__.py
│   └── monte_carlo.py            # Monte Carlo
└── agents/
    ├── README.md                 # 에이전트 개요
    ├── agent_01_suitability.md   # 설문 분석
    ├── agent_03_portfolio_constructor.md
    ├── agent_06_counterfactual.md
    └── AGENTS_SUMMARY.md
```

---

## 🔧 필요 라이브러리

```bash
pip install numpy pandas scipy scikit-learn cvxpy
```

**requirements.txt** 업데이트 완료 ✅

---

## 📊 사용 예시

```python
from fund_manager.construction import PortfolioGenerator, IPS
import pandas as pd

# 1. 수익률 데이터 준비
returns = pd.DataFrame({
    'Stock_A': [...],
    'Stock_B': [...],
    'Bond_ETF': [...]
})

# 2. IPS 정의
ips = IPS(
    risk_level=3,
    target_vol=0.15,
    max_drawdown_target=0.20,
    cvar_limit_95=0.12,
    equity_range=(0.4, 0.8),
    rebalance_band=0.05
)

# 3. 포트폴리오 생성
generator = PortfolioGenerator(returns, ips)
portfolios = generator.generate_three_portfolios(
    initial_capital=50_000_000,  # 5천만원
    time_horizon_months=60,      # 5년
    target_amount=75_000_000     # 목표 7천5백만원
)

# 4. 결과 확인
for name, portfolio in portfolios.items():
    print(f"{portfolio.name}:")
    print(f"  기대수익률: {portfolio.expected_return:.2%}")
    print(f"  목표 달성 확률: {portfolio.goal_achievement_prob:.2%}")
```

---

## ✅ 검증 완료

각 알고리즘은 독립적으로 실행 가능한 예제 포함:
- `python fund_manager/construction/hrp.py`
- `python fund_manager/construction/cvar_constraint.py`
- `python fund_manager/forecast/monte_carlo.py`
- `python fund_manager/construction/generator.py`

---

## 다음 단계

### Phase 1: API 통합
1. **Pydantic 모델** - Request/Response schemas
2. **API 엔드포인트** - `/api/fund/construct` 구현
3. **에이전트 연결** - CrewAI 통합

### Phase 2: Universe Curator
- 국내/해외 종목 선정 로직
- ETF 필터링

### Phase 3: Counterfactual
- 파라미터 변경 시뮬레이션
- "만약 ~였다면" 비교

### Phase 4: Monitoring
- Living Fund State Machine
- Rebalancing 제안

---

## 🎓 핵심 기술 스택

| 기술 | 용도 |
|------|------|
| **scipy** | 계층적 클러스터링 |
| **scikit-learn** | 클러스터링 알고리즘 |
| **cvxpy** | Convex Optimization |
| **numpy** | 행렬 연산 |
| **pandas** | 데이터 처리 |

---

## 📖 참고 문헌

1. **HRP**: López de Prado, M. (2016). "Building Diversified Portfolios that Outperform Out of Sample"
2. **CVaR**: Rockafellar, R.T., & Uryasev, S. (2000). "Optimization of conditional value-at-risk"
3. **Monte Carlo**: Glasserman, P. (2003). "Monte Carlo Methods in Financial Engineering"

---

**작성일**: 2026-01-04
**버전**: 1.0
**상태**: 알고리즘 구현 완료 ✅
