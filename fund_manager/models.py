"""
Fund Manager - Pydantic Models

API Request/Response 모델 정의
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum


# ============================================================
# Enums
# ============================================================

class IncomeStability(str, Enum):
    stable = "stable"
    moderate = "moderate"
    unstable = "unstable"

class VolatilityComfort(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"

class LossReaction(str, Enum):
    panic = "panic"
    concern = "concern"
    acceptance = "acceptance"

class DecisionStyleType(str, Enum):
    loss_averse = "loss-averse"
    regret_averse = "regret-averse"
    probability_driven = "probability-driven"
    narrative_driven = "narrative-driven"

class ConcentrationPreference(str, Enum):
    diversified = "diversified"
    focused = "focused"
    concentrated = "concentrated"

class RebalanceTolerance(str, Enum):
    frequent = "frequent"
    moderate = "moderate"
    patient = "patient"


# ============================================================
# Request Models
# ============================================================

class SuitabilityRequest(BaseModel):
    """설문 응답 (POST /api/fund/suitability)"""
    investable_amount: float = Field(..., description="투자 가능 금액 (원)")
    investment_period_months: int = Field(..., description="투자 기간 (개월)")
    max_loss_tolerance_pct: float = Field(..., description="최대 손실 허용 (%)")
    target_annual_return_pct: float = Field(..., description="목표 연 수익률 (%)")
    income_stability: IncomeStability = Field(..., description="소득 안정성")
    emergency_fund_months: int = Field(..., description="비상 자금 (개월)")
    investment_experience: str = Field(..., description="투자 경험")
    knowledge_level: str = Field(..., description="지식 수준")
    loss_reaction: LossReaction = Field(..., description="손실 반응")
    volatility_comfort: VolatilityComfort = Field(..., description="변동성 편안함")
    concentration_preference: ConcentrationPreference = Field(..., description="집중도 선호")
    rebalance_tolerance: RebalanceTolerance = Field(..., description="리밸런싱 허용")
    fx_exposure_tolerance: str = Field(default="medium", description="환율 노출 허용")


class HoldingInput(BaseModel):
    ticker: str
    amount: float
    name: Optional[str] = None

class UniverseRequest(BaseModel):
    """유니버스 구성 요청 (POST /api/fund/universe)"""
    decision_profile_id: Optional[str] = Field(None, description="프로파일 ID")
    region_preference: Dict[str, float] = Field(..., description="지역 선호 (domestic_pct, overseas_pct)")
    asset_types: List[str] = Field(default=["stock", "etf"], description="자산 유형")
    exclude_sectors: List[str] = Field(default=[], description="제외 섹터")
    include_themes: List[str] = Field(default=[], description="포함 테마")
    min_market_cap: Optional[float] = Field(None, description="최소 시가총액")
    max_volatility: Optional[float] = Field(None, description="최대 변동성")
    user_holdings: List[HoldingInput] = Field(default=[], description="현재 보유 종목")


class UserView(BaseModel):
    """사용자 뷰 (Black-Litterman용)"""
    asset: str = Field(..., description="자산/섹터")
    view_type: str = Field(..., description="bullish/bearish")
    confidence: float = Field(..., description="신뢰도 (0-1)")
    expected_return_adjustment: float = Field(..., description="기대수익 조정 (%)")


class ConstructionRequest(BaseModel):
    """포트폴리오 생성 요청 (POST /api/fund/construct)"""
    decision_profile_id: Optional[str] = None
    ips_id: Optional[str] = None
    ips: Optional[Dict[str, Any]] = Field(None, description="IPS (Investment Policy Statement)")
    universe: List[Dict] = Field(..., description="투자 유니버스")
    user_views: List[UserView] = Field(default=[], description="사용자 뷰")
    investment_goal: Dict = Field(..., description="투자 목표 (target_amount, target_date)")
    initial_capital: float = Field(..., description="초기 자본")
    user_holdings: List[HoldingInput] = Field(default=[], description="현재 보유 종목 (Rebalancing용)")


# ============================================================
# Response Models
# ============================================================

class RiskCapacity(BaseModel):
    """재무적 감당력"""
    investable_amount: float
    time_horizon_months: int
    income_stability: str
    emergency_fund_months: int
    assessment: str


class RiskPreference(BaseModel):
    """심리적 감내도"""
    max_tolerable_loss_pct: float
    volatility_comfort: str
    loss_reaction: str
    assessment: str


class DecisionStyle(BaseModel):
    """의사결정 스타일"""
    type: str
    concentration_preference: str
    rebalance_tolerance: str
    assessment: str


class DecisionProfile(BaseModel):
    """3축 프로파일"""
    risk_capacity: RiskCapacity
    risk_preference: RiskPreference
    decision_style: DecisionStyle


class IPS(BaseModel):
    """Investment Policy Statement"""
    risk_level: int
    horizon_months: int # 투자 기간 (개월)
    target_vol: float # 목표 연 변동성
    max_drawdown_target: float # 최대 낙폭 한도
    cvar_limit_95: float # 95% CVaR 한도
    equity_range: List[float] # [Min, Max]
    fx_exposure_limit: Optional[float] = 1.0 # 환노출 한도 (1.0 = 100%)
    turnover_budget: Optional[float] = 0.5 # 분기 회전율 한도
    rebalance_band: float # 리밸런싱 밴드
    loss_reaction_threshold: int # 손실 인내심 점수


class SuitabilityResponse(BaseModel):
    """설문 분석 응답"""
    decision_profile: DecisionProfile
    ips: IPS
    profile_summary: str
    key_insights: List[str]


class UniverseItem(BaseModel):
    """유니버스 항목"""
    ticker: str
    name: str
    asset_type: str
    region: str
    sector: Optional[str] = None
    theme: Optional[str] = None
    market_cap: Optional[float] = None
    avg_volatility_1y: Optional[float] = None
    avg_return_1y: Optional[float] = None
    liquidity_score: Optional[int] = None


class UniverseResponse(BaseModel):
    """유니버스 응답"""
    universe: List[UniverseItem]
    stats: Dict[str, int]


class Holding(BaseModel):
    """보유 종목"""
    ticker: str
    name: str
    asset_type: str
    region: str
    sector: Optional[str] = None
    weight: float
    amount_krw: float
    shares_est: Optional[int] = None
    rationale: str


class ForecastDistribution(BaseModel):
    """예측 분포"""
    return_p10: float
    return_p50: float
    return_p90: float
    volatility: float
    max_drawdown_est: float
    cvar_95: float
    goal_achievement_prob: float


class ScenarioResult(BaseModel):
    """시나리오 결과"""
    impact_pct: float
    description: str


class PsychologicalStress(BaseModel):
    """심리적 압박 분석"""
    consecutive_loss_days_est: int
    recovery_time_est_months: int
    dropout_probability: float
    methodology_note: str


class RiskSummary(BaseModel):
    market: str
    currency: str
    liquidity: str
    strategy: str

class RebalancingGuide(BaseModel):
    periodic: str
    risk_control: str
    smart_alert: str

class Explainability(BaseModel):
    """설명"""
    portfolio_name_fancy: Optional[str] = None
    slogan: Optional[str] = None
    investment_goal_summary: Optional[str] = None
    risk_summary: Optional[RiskSummary] = None
    rebalancing_guide: Optional[RebalancingGuide] = None
    why_this_portfolio: List[str]
    main_risk_factors: List[str]
    why_not_others: List[str]
    what_to_watch: List[str]


class Portfolio(BaseModel):
    """포트폴리오"""
    name: str
    description: str
    holdings: List[Holding]
    total_holdings_count: int
    domestic_weight: float
    overseas_weight: float
    equity_weight: float
    fixed_income_weight: Optional[float] = 0.0
    cash_weight: Optional[float] = 0.0
    sector_exposure: Optional[Dict[str, float]] = None
    forecast: ForecastDistribution
    scenarios: Optional[Dict[str, ScenarioResult]] = None
    psychological_stress: PsychologicalStress
    suitability_score: float
    explainability: Explainability


class ConstructionResponse(BaseModel):
    """포트폴리오 생성 응답"""
    portfolios: List[Portfolio]
    construction_log: Dict[str, Any]
