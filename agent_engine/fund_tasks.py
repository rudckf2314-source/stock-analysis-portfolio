"""
Fund Manager Tasks for CrewAI

기존 agent_engine을 활용한 펀드 매니저 tasks
"""

from crewai import Task


def create_suitability_task(agent, survey_data: dict) -> Task:
    """
    설문 분석 → IPS 생성 Task
    
    기존 Data Analyst Agent 활용
    """
    return Task(
        description=f"""
        사용자 투자 설문을 분석하여 3축 프로파일과 IPS(Investment Policy Statement)를 생성하세요.
        
        설문 데이터:
        {survey_data}
        
        다음 3가지를 분석하세요:
        
        1. **Risk Capacity (재무적 감당력)**
           - 투자 가능 금액: {survey_data.get('investable_amount', 0):,}원
           - 투자 기간: {survey_data.get('investment_period_months', 0)}개월
           - 소득 안정성: {survey_data.get('income_stability', 'unknown')}
           - 비상 자금: {survey_data.get('emergency_fund_months', 0)}개월
           
        2. **Risk Preference (심리적 감내도)**
           - 최대 손실 허용: {survey_data.get('max_loss_tolerance_pct', 0)}%
           - 변동성 편안함: {survey_data.get('volatility_comfort', 'unknown')}
           - 손실 반응: {survey_data.get('loss_reaction', 'unknown')}
           
        3. **Decision Style (의사결정 스타일)**
           - 집중도 선호: {survey_data.get('concentration_preference', 'unknown')}
           - 리밸런싱 허용: {survey_data.get('rebalance_tolerance', 'unknown')}
        
        출력 형식:
        {{
            "decision_profile": {{
                "risk_capacity": {{
                    "investable_amount": <float>,
                    "time_horizon_months": <int>,
                    "income_stability": "stable|moderate|unstable",
                    "emergency_fund_months": <int>,
                    "assessment": "<재무적 감당력 평가>"
                }},
                "risk_preference": {{
                    "max_tolerable_loss_pct": <float>,
                    "volatility_comfort": "low|medium|high",
                    "loss_reaction": "panic|concern|acceptance",
                    "assessment": "<심리적 감내도 평가>"
                }},
                "decision_style": {{
                    "type": "loss-averse|regret-averse|probability-driven|narrative-driven",
                    "concentration_preference": "diversified|focused|concentrated",
                    "rebalance_tolerance": "frequent|moderate|patient",
                    "assessment": "<의사결정 스타일 설명>"
                }}
            }},
            "ips": {{
                "risk_level": <1-5>,
                "target_vol": <0.05-0.30>,
                "max_drawdown_target": <0.10-0.50>,
                "cvar_limit_95": <0.05-0.25>,
                "equity_range": [<min>, <max>],
                "rebalance_band": <0.03-0.10>,
                "loss_reaction_threshold": <5-30>
            }},
            "profile_summary": "<한 문장 요약>",
            "key_insights": ["<인사이트 1>", "<인사이트 2>", ...]
        }}
        
        중요: 재무적 능력과 심리적 의지를 구분하세요. IPS는 더 보수적인 쪽에 맞추세요.
        """,
        expected_output="JSON format decision profile and IPS",
        agent=agent
    )


def create_portfolio_construction_task(agent, universe: list, ips: dict, capital: float) -> Task:
    """
    포트폴리오 생성 Task
    
    기존 Strategy Agent 활용
    """
    universe_str = "\n".join([
        f"- {asset['ticker']} ({asset['name']}): {asset['asset_type']}, {asset['region']}"
        for asset in universe
    ])
    
    return Task(
        description=f"""
        다음 투자 유니버스와 IPS를 기반으로 3가지 포트폴리오를 생성하세요:
        
        투자 유니버스 ({len(universe)}개 자산):
        {universe_str}
        
        IPS (Investment Policy Statement):
        - Risk Level: {ips.get('risk_level', 3)}
        - Target Volatility: {ips.get('target_vol', 0.15):.2%}
        - Max Drawdown: {ips.get('max_drawdown_target', 0.20):.2%}
        - CVaR Limit (95%): {ips.get('cvar_limit_95', 0.12):.2%}
        - Equity Range: {ips.get('equity_range', (0.4, 0.8))}
        
        초기 자본: {capital:,}원
        
        다음 3가지 포트폴리오를 생성하세요:
        
        1. **Base Case**: 가장 균형잡힌 포트폴리오
           - IPS 제약을 충실히 반영
           - 분산 투자 원칙
           
        2. **Upside-Seeking**: 수익 극대화 버전
           - 동일 IPS 제약 내에서 기대수익 최대화
           - 고수익 자산 비중↑
           
        3. **Downside-Defensive**: 손실 최소화 버전
           - 안정 자산 비중 확대
           - CVaR를 목표보다 낮게
        
        각 포트폴리오마다 다음을 제시하세요:
        - 보유 종목 및 비중
        - 예상 수익률/변동성
        - 국내/해외 비중
        - 각 종목 선정 근거
        
        출력 형식:
        {{
            "portfolios": [
                {{
                    "name": "Base",
                    "description": "설명",
                    "holdings": [
                        {{
                            "ticker": "...",
                            "name": "...",
                            "weight": <0-1>,
                            "rationale": "선정 이유"
                        }}
                    ],
                    "expected_return": <float>,
                    "expected_volatility": <float>,
                    "domestic_weight": <float>,
                    "overseas_weight": <float>
                }},
                ...
            ]
        }}
        
        중요: 3가지 포트폴리오는 우열이 아니라 서로 다른 철학을 대표합니다.
        """,
        expected_output="JSON format with 3 portfolios",
        agent=agent
    )


def create_explainability_task(agent, portfolios: list) -> Task:
    """
    설명 생성 Task
    
    기존 Report Writer Agent 활용
    """
    return Task(
        description=f"""
        [MANDATORY PHILOSOPHY]
        You are a Real Fund Manager acting under strict fiduciary duty.
        You must ground your advice in **Academic Theories and Research** (MPT, Prospect Theory, etc.).
        
        [TASK OBJECTIVE]
        Provide a DETAILED, PROFESSIONAL explanation for the 3 generated portfolios.
        The user wants to see clear names, goals, risks, and rebalancing rules.
        Make each portfolio distinct and full of character.
        
        [OUTPUT FORMAT]
        Update the JSON with the following fields for each portfolio:
        
        "explainability": {{
            "portfolio_name_fancy": "<Creative Name (e.g. 'AI Smart Growth 3y')>",
            "slogan": "<Catchy Slogan (e.g. '(AI가 24시간 지켜보는 내 자산)')>",
            "investment_goal_summary": "<One sentence goal (e.g. '투자기간 3년, 연 목표수익 7%, 최대낙폭 -15% 제한')>",
            
            "risk_summary": {{
                "market": "<Market Risk: 경기 변동에 따른 변동성>",
                "currency": "<Currency Risk: 환율 변동에 따른 가치 변화>",
                "liquidity": "<Liquidity Risk: 급변 시 매도 제한>",
                "strategy": "<Strategy Risk: 특정 섹터 부진 가능성>"
            }},
            
            "rebalancing_guide": {{
                "periodic": "6개월 정기 리밸런싱", 
                "risk_control": "MDD 한도 근접 시 방어 로직 가동",
                "smart_alert": "시장 급변 시 실시간 알림"
            }},

            "why_this_portfolio": [
                "Logic: <Core Logic>",
                "Theoretical Basis: <Academic Theory (e.g. Risk Parity)>",
                "Suitability: <Why it fits the user>"
            ],
            "main_risk_factors": [
                "Scenario: <Crisis outcome>",
                "Concentration: <Warning>"
            ],
            "why_not_others": [
                "vs Upside: ...",
                "vs Defensive: ..."
            ],
            "what_to_watch": [
                "Trigger: ...",
                "Indicator: ..."
            ]
        }}
        
        Tone: Professional, Objective, Academic but Accessible.
        Language: Korean.
        """,
        expected_output="JSON with explainability for each portfolio",
        agent=agent
    )
