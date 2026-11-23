"""
Fund Manager Crew Functions

펀드 매니저 **전용 에이전트**를 사용한 분석 함수들
"""

import json
import re
from crewai import Crew, Process
from agent_engine.fund_agents import create_fund_manager_agents
from agent_engine.fund_tasks import (
    create_suitability_task,
    create_portfolio_construction_task,
    create_explainability_task
)


from agent_engine.agents import create_news_analyst_agent
from langchain_openai import ChatOpenAI
from crewai import Task


def _extract_json(text: str) -> dict:
    """
    Robust JSON extraction from mixed text.
    Handles Markdown code blocks and raw JSON structures.
    Iterates through potential JSON blocks if the first one is invalid.
    """
    # 1. Try Markdown code blocks first (Most reliable)
    code_block_pattern = r'```json\s*(\{[\s\S]*?\})\s*```'
    matches = re.finditer(code_block_pattern, text, re.IGNORECASE)
    for match in matches:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            continue

    # 2. Try raw JSON extraction with brace counting
    # We iterate through every '{' to find a valid JSON object
    cursor = 0
    while True:
        start_idx = text.find('{', cursor)
        if start_idx == -1:
            break
            
        stack = 0
        for i in range(start_idx, len(text)):
            if text[i] == '{':
                stack += 1
            elif text[i] == '}':
                stack -= 1
                if stack == 0:
                    # Found a complete block
                    json_candidate = text[start_idx:i+1]
                    try:
                        return json.loads(json_candidate)
                    except json.JSONDecodeError:
                        # Not valid JSON (e.g. {note}), keep searching from this closing brace
                        break 
        
        # Move cursor forward to find next '{'
        cursor = start_idx + 1
        
    raise ValueError("Failed to extract valid JSON from agent output")


def run_suitability_analysis(survey_data: dict, model_name: str = "gpt-4o") -> dict:
    """
    설문 분석 → IPS 생성 (Suitability Specialist Only)
    
    [Modification]
    - 시장 뉴스 분석(News Analyst) 제거하여 기능 분리 및 속도 향상.
    - 오직 사용자 설문 데이터(Survey Data)에 기반한 정밀 프로파일링 수행.
    
    Args:
        survey_data: 사용자 설문 응답
        model_name: OpenAI 모델명
        
    Returns:
        DecisionProfile + IPS
    """
    print(f"\n{'='*60}")
    print(f"[INFO] Suitability Analysis Started (User Profile Focused)")
    print(f"{'='*60}\n")
    
    try:
        # 1. Agents 생성 
        # (순수 펀드매니저 에이전트만 사용)
        fund_agents = create_fund_manager_agents(model_name=model_name)
        suitability_agent = fund_agents['suitability_specialist']
        
        # 2. Tasks 생성
        suitability_task = create_suitability_task(suitability_agent, survey_data)
        
        # 3. Crew 구성 (Single Agent)
        crew = Crew(
            agents=[suitability_agent],
            tasks=[suitability_task],
            process=Process.sequential,
            verbose=True
        )
        
        # Execute
        print(f"[INFO] Analyzing Investor Profile...\n")
        result = crew.kickoff()
        
        # Parse JSON
        result_str = str(result)
        parsed = _extract_json(result_str)
        
        print(f"[SUCCESS] Suitability Analysis Complete (Integrated)\n")
        return parsed
            
    except Exception as e:
        print(f"[ERROR] Suitability Analysis Failed: {e}")
        raise


def run_portfolio_construction(universe: list, ips: dict, capital: float, model_name: str = "gpt-4o") -> dict:
    """
    포트폴리오 생성 (**전용 Portfolio Architect 사용**)
    
    Args:
        universe: 투자 유니버스
        ips: Investment Policy Statement
        capital: 초기 자본
        model_name: OpenAI 모델명
        
    Returns:
        3가지 포트폴리오
    """
    print(f"\n{'='*60}")
    print(f"[INFO] Portfolio Construction Started (Dedicated Agent)")
    print(f"{'='*60}\n")
    
    try:
        # Fund Manager 전용 에이전트 생성
        agents = create_fund_manager_agents(model_name=model_name)
        
        # Construction task (전용 Portfolio Architect 사용)
        task = create_portfolio_construction_task(
            agents['portfolio_architect'], 
            universe, 
            ips, 
            capital
        )
        
        # Single-agent crew
        crew = Crew(
            agents=[agents['portfolio_architect']],
            tasks=[task],
            process=Process.sequential,
            verbose=True
        )
        
        print(f"[INFO] Generating 3 portfolios with Portfolio Architect...\n")
        result = crew.kickoff()
        
        # Parse JSON
        result_str = str(result)
        parsed = _extract_json(result_str)
        
        print(f"[SUCCESS] Portfolio Construction Complete (Dedicated Agent)\n")
        return parsed
            
    except Exception as e:
        print(f"[ERROR] Portfolio Construction Failed: {e}")
        raise


def run_portfolio_explainability(portfolios: list, model_name: str = "gpt-4o") -> dict:
    """
    설명 생성 (**전용 Explainability Specialist 사용**)
    
    Args:
        portfolios: 생성된 포트폴리오 리스트
        model_name: OpenAI 모델명
        
    Returns:
        Explainability 추가된 포트폴리오
    """
    print(f"\n{'='*60}")
    print(f"[INFO] Explainability Generation Started (Dedicated Agent)")
    print(f"{'='*60}\n")
    
    try:
        # Fund Manager 전용 에이전트 생성
        agents = create_fund_manager_agents(model_name=model_name)
        
        # Explainability task (전용 Explainability Specialist 사용)
        task = create_explainability_task(agents['explainability_specialist'], portfolios)
        
        # Single-agent crew
        crew = Crew(
            agents=[agents['explainability_specialist']],
            tasks=[task],
            process=Process.sequential,
            verbose=True
        )
        
        print(f"[INFO] Adding explanations with Explainability Specialist...\n")
        result = crew.kickoff()
        
        # Parse JSON
        result_str = str(result)
        parsed = _extract_json(result_str)
        
        print(f"[SUCCESS] Explainability Complete (Dedicated Agent)\n")
        return parsed
            
    except Exception as e:
        print(f"[ERROR] Explainability Failed: {e}")
        raise


if __name__ == "__main__":
    # Test suitability
    test_survey = {
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
    }
    
    result = run_suitability_analysis(test_survey)
    print(json.dumps(result, indent=2, ensure_ascii=False))
