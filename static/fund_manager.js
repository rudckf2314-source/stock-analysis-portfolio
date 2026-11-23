/**
 * Fund Manager - Frontend Logic
 * 
 * AI 기반 맞춤형 포트폴리오 설계 및 운용
 */

let currentFundStep = 1;
let surveyData = null;
let suitabilityResult = null;
let portfoliosResult = null;
let userHoldings = []; // 사용자 보유 종목 (Optional)

// 상세 로딩 메시지
const LOADING_MESSAGES = {
    1: [
        "투자 성향 데이터를 정밀 분석 중입니다...",
        "위험 감수 성향(Risk Profile)을 스코어링하고 있습니다...",
        "적정 목표 수익률과 변동성 허용 한도를 계산 중입니다...",
        "비상금 및 유동성 제약 조건을 검토하고 있습니다..."
    ],
    2: [
        "글로벌 자산 유니버스(Stock Universe)를 스캔 중입니다...",
        "미국/한국 시장의 거시경제 지표(금리, 환율)를 수집 중입니다...",
        "기존 보유 종목의 리스크 요인을 분석하고 있습니다...",
        "섹터별 모멘텀과 밸류에이션 매력도를 평가 중입니다..."
    ],
    3: [
        "Mean-Variance 최적화 모델을 가동하고 있습니다...",
        "몬테카를로 시뮬레이션(1,000회)으로 리스크를 검증 중입니다...",
        "포트폴리오별 예상 최대 낙폭(MDD)을 시뮬레이션 중입니다...",
        "최종 투자 제안서(Proposal) 및 리밸런싱 가이드를 작성 중입니다..."
    ]
};
let loadingInterval = null;

// ============================================================
// Survey Form Handling
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    const surveyForm = document.getElementById('surveyForm');
    const analyzeBtn = document.getElementById('btnStartAnalysis');

    // Prevent default form submission (e.g. Enter key)
    if (surveyForm) {
        surveyForm.addEventListener('submit', (e) => {
            e.preventDefault();
        });
    }

    // Handle Button Click Manually
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', (e) => {
            console.log("Button Clicked");
            e.preventDefault();
            handleSurveySubmit(e);
        });
    }

    // Explicitly expose to window for inline onclick safety
    window.handleSurveySubmit = handleSurveySubmit;

    // --- Existing Holdings UI ---
    const checkbox = document.getElementById('hasExistingHoldings');
    const section = document.getElementById('existingHoldingsSection');
    const btnAdd = document.getElementById('btnAddHolding');
    const inputTicker = document.getElementById('holdingTickerInput');
    const inputAmount = document.getElementById('holdingAmountInput');
    const list = document.getElementById('holdingsList');
    const totalEl = document.getElementById('totalHoldingsAmount');

    if (checkbox && section) {
        checkbox.addEventListener('change', (e) => {
            section.style.display = e.target.checked ? 'block' : 'none';
        });
    }

    if (btnAdd) {
        btnAdd.addEventListener('click', () => {
            const ticker = inputTicker.value.trim().toUpperCase();
            const amount = parseFloat(inputAmount.value);

            if (!ticker || isNaN(amount) || amount <= 0) {
                alert('종목명과 유효한 금액을 입력해주세요.');
                return;
            }

            userHoldings.push({ ticker, amount, name: ticker });
            renderHoldingsList();

            inputTicker.value = '';
            inputAmount.value = '';
            inputTicker.focus();
        });
    }

    function renderHoldingsList() {
        if (!list) return;
        list.innerHTML = userHoldings.map((h, i) => `
            <li style="display:flex; justify-content:space-between; align-items:center; padding:8px; border-bottom:1px solid #f1f5f9;">
                <span style="font-weight:600; color:#334155;">${h.ticker}</span>
                <div style="display:flex; align-items:center;">
                    <span style="margin-right:10px; color:#64748b; font-size:0.9em;">${h.amount.toLocaleString()}원</span>
                    <button type="button" onclick="removeUserHolding(${i})" style="color:#ef4444; border:none; background:none; cursor:pointer; font-weight:bold;">✕</button>
                </div>
            </li>
        `).join('');

        const total = userHoldings.reduce((sum, h) => sum + h.amount, 0);
        if (totalEl) totalEl.textContent = `총 보유액: ${total.toLocaleString()}원`;
    }

    // Global exposure for onClick
    window.removeUserHolding = (index) => {
        userHoldings.splice(index, 1);
        renderHoldingsList();
    };
});

async function handleSurveySubmit(e) {
    if (e && e.preventDefault) e.preventDefault();

    const form = document.getElementById('surveyForm');
    if (!form) return;

    // Validate Form
    if (!form.checkValidity()) {
        form.reportValidity();
        return;
    }

    const formData = new FormData(form);
    surveyData = Object.fromEntries(formData.entries());

    // Convert numbers (Million Won Unit Handling)
    if (surveyData.investable_amount_raw) {
        surveyData.investable_amount = parseFloat(surveyData.investable_amount_raw) * 1000000;
    } else {
        // Fallback if needed
        surveyData.investable_amount = parseFloat(surveyData.investable_amount || 0);
    }

    surveyData.investment_period_months = parseInt(surveyData.investment_period_months);
    surveyData.target_annual_return_pct = parseFloat(surveyData.target_annual_return_pct);
    surveyData.max_loss_tolerance_pct = parseFloat(surveyData.max_loss_tolerance_pct);
    surveyData.emergency_fund_months = parseInt(surveyData.emergency_fund_months);

    console.log('📝 Survey Data:', surveyData);

    // Move to step 2 immediately
    moveToStep(2);

    // Explicitly force Step 2 visibility (Safety Net)
    const step2 = document.querySelector('.fund-step-content[data-step-content="2"]');
    if (step2) {
        step2.classList.add('active');
        step2.style.display = 'block';
    }

    // Run analysis
    await runFundManagerAnalysis();
}

// ============================================================
// Fund Manager Analysis
// ============================================================

async function runFundManagerAnalysis() {
    console.log("[DEBUG] Analysis Started");

    // [Fix] Force Display Loading Screen (렌더링 이슈 방지)
    const loadingDiv = document.getElementById('fundLoading');
    const resultsDiv = document.getElementById('fundResults');
    const step2Content = document.querySelector('.fund-step-content[data-step-content="2"]');

    // Step 2 컨테이너가 닫혀있을 경우를 대비해 강제 오픈
    if (step2Content) {
        step2Content.style.cssText = "display: block !important; opacity: 1 !important; visibility: visible !important; min-height: 500px !important;";
        step2Content.classList.add('active');
    }

    if (loadingDiv) {
        // 인라인 스타일 강력 적용
        loadingDiv.style.cssText = "display: block !important; visibility: visible !important; opacity: 1 !important; background: #fff !important; z-index: 9999 !important; padding: 50px !important; margin-top: 20px;";
    }

    if (resultsDiv) {
        resultsDiv.style.display = 'none';
    }

    // 약간의 지연 후 메시지 업데이트 (UI 갱신 시간 확보)
    await new Promise(r => setTimeout(r, 100));

    // alert("[Debug] 로딩 화면이 보여야 합니다. 확인 후 서버 요청 시작.");

    updateFundLoadingStatus('Step 1/3: 투자 성향 분석 중...');

    try {
        // Step 1: Suitability Analysis
        const suitabilityResponse = await fetch('/api/fund/suitability', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(surveyData)
        });

        if (!suitabilityResponse.ok) {
            throw new Error('Suitability analysis failed');
        }

        suitabilityResult = await suitabilityResponse.json();
        console.log('[DEBUG] Suitability Result:', suitabilityResult);

        updateFundLoadingStatus('Step 2/3: 투자 유니버스 구성 중...');

        // Step 2: Universe Construction
        const universeResponse = await fetch('/api/fund/universe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                region_preference: {
                    domestic_pct: 50,
                    overseas_pct: 50
                },
                asset_types: ['stock', 'etf'],
                user_holdings: userHoldings // 전달
            })
        });

        if (!universeResponse.ok) {
            throw new Error('Universe construction failed');
        }

        const universeResult = await universeResponse.json();
        console.log('[DEBUG] Universe Result:', universeResult);

        updateFundLoadingStatus('Step 3/3: 포트폴리오 생성 중...');

        // Step 3: Portfolio Construction
        const constructionResponse = await fetch('/api/fund/construct', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                universe: universeResult.universe,
                initial_capital: surveyData.investable_amount,
                ips: suitabilityResult.ips,  // ✅ IPS 데이터 전달 (진짜 분석용)
                investment_goal: {
                    target_amount: surveyData.investable_amount * (1 + surveyData.target_annual_return_pct / 100),
                    target_date: new Date(Date.now() + surveyData.investment_period_months * 30 * 24 * 60 * 60 * 1000).toISOString()
                },
                user_views: [],
                user_holdings: userHoldings // 전달
            })
        });

        if (!constructionResponse.ok) {
            throw new Error('Portfolio construction failed');
        }

        portfoliosResult = await constructionResponse.json();
        console.log('[DEBUG] Portfolios Result:', portfoliosResult);

        // Display results
        displayFundResults();

    } catch (error) {
        console.error('[ERROR] Fund Manager Analysis Error:', error);

        stopLoadingSequence();
        const loadingDiv = document.getElementById('fundLoading');
        if (loadingDiv) loadingDiv.style.display = 'none';

        alert('분석 중 오류가 발생했습니다: ' + error.message);
        moveToStep(1); // Go back to survey
    }
}

// ============================================================
// Results Display
// ============================================================

function displayFundResults() {
    console.log("[DEBUG] Displaying Fund Results (Reconstruction Mode)...");
    stopLoadingSequence();

    // 1. Get the Step 2 Container
    const step2Container = document.querySelector('.fund-step-content[data-step-content="2"]');
    if (!step2Container) {
        console.error("Step 2 Container not found! Check selector .fund-step-content[data-step-content='2']");
        return;
    }
    console.log("✅ Step 2 Container Found:", step2Container);

    // 2. FORCE Visible Parent
    step2Container.style.cssText = "display: block !important; visibility: visible !important; height: auto !important; min-height: 500px;";
    step2Container.classList.add('active');

    // 3. Clear current content (removes Loading div and old Results div)
    step2Container.innerHTML = '';

    // 4. Create Fresh Results Container
    const resultsContainer = document.createElement('div');
    resultsContainer.id = 'fundResults';
    resultsContainer.className = 'fund-results';
    resultsContainer.style.cssText = "display: block !important; opacity: 1 !important; visibility: visible !important; width: 100%;";

    // 5. Build Inner HTML Structure
    resultsContainer.innerHTML = `
        <!-- IPS Summary -->
        <div class="ips-card">
            <h3 class="ips-title">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 8px;"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path><rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect></svg>
                투자 정책서 (IPS)
            </h3>
            <div class="ips-content" id="ipsContent"></div>
        </div>

        <!-- Portfolio Comparison -->
        <div class="portfolios-section">
            <h3 class="portfolios-title">추천 포트폴리오 (3가지)</h3>
            <p class="portfolios-subtitle">AI가 귀하의 성향에 맞춰 설계한 3가지 전략입니다.</p>
            <div class="portfolios-grid" id="portfoliosGrid"></div>
        </div>
    `;

    // 6. Inject into DOM
    step2Container.appendChild(resultsContainer);

    // 7. Populate Data
    setTimeout(() => {
        try {
            displayIPS();
            displayPortfolios();
            console.log("✅ Fund Results Reconstructed & Displayed");
        } catch (e) {
            console.error("Rendering Error:", e);
            step2Container.innerHTML = `<div style="color:red; padding:20px;">결과 렌더링 오류: ${e.message}</div>`;
        }
    }, 50);
}



function displayIPS() {
    const ipsContent = document.getElementById('ipsContent');
    const ips = suitabilityResult.ips;
    const profile = suitabilityResult.decision_profile;

    ipsContent.innerHTML = `
        <div class="ips-grid">
            <div class="ips-item">
                <div class="ips-label">위험 수준</div>
                <div class="ips-value">Level ${ips.risk_level || 3}/5</div>
            </div>
            <div class="ips-item">
                <div class="ips-label">목표 변동성</div>
                <div class="ips-value">${((ips.target_vol || 0.15) * 100).toFixed(1)}%</div>
            </div>
            <div class="ips-item">
                <div class="ips-label">최대 낙폭 목표</div>
                <div class="ips-value">${((ips.max_drawdown_target || 0.20) * 100).toFixed(0)}%</div>
            </div>
            <div class="ips-item">
                <div class="ips-label">CVaR 한도 (95%)</div>
                <div class="ips-value">${((ips.cvar_limit_95 || 0.15) * 100).toFixed(1)}%</div>
            </div>
            <div class="ips-item">
                <div class="ips-label">주식 비중 범위</div>
                <div class="ips-value">${((ips.equity_range?.[0] || 0.3) * 100).toFixed(0)}% ~ ${((ips.equity_range?.[1] || 0.7) * 100).toFixed(0)}%</div>
            </div>
            <div class="ips-item">
                <div class="ips-label">리밸런싱 밴드</div>
                <div class="ips-value">±${((ips.rebalance_band || 0.05) * 100).toFixed(0)}%</div>
            </div>
        </div>
        
        <div class="profile-summary">
            <h4>투자자 프로파일</h4>
            <p>${suitabilityResult.profile_summary}</p>
            <ul class="key-insights">
                ${suitabilityResult.key_insights.map(insight => `<li>${insight}</li>`).join('')}
            </ul>
        </div>
    `;
}

function displayPortfolios() {
    const portfoliosGrid = document.getElementById('portfoliosGrid');
    const portfolios = portfoliosResult.portfolios;

    portfoliosGrid.innerHTML = portfolios.map((portfolio, index) => `
        <div class="portfolio-card" data-portfolio="${index}">
            <div class="portfolio-header">
                <h4 class="portfolio-name">${portfolio.name}</h4>
                <p class="portfolio-description">${portfolio.description}</p>
            </div>
            
            <div class="portfolio-metrics">
                <div class="portfolio-metric">
                    <div class="metric-label">기대 수익률</div>
                    <div class="metric-value">${(portfolio.forecast.return_p50 * 100).toFixed(1)}%</div>
                </div>
                <div class="portfolio-metric">
                    <div class="metric-label">변동성</div>
                    <div class="metric-value">${(portfolio.forecast.volatility * 100).toFixed(1)}%</div>
                </div>
                <div class="portfolio-metric">
                    <div class="metric-label">목표 달성 확률</div>
                    <div class="metric-value">${(portfolio.forecast.goal_achievement_prob * 100).toFixed(0)}%</div>
                </div>
            </div>
            
            <div class="portfolio-weights">
                <div class="weight-item">
                    <span>국내</span>
                    <span>${(portfolio.domestic_weight * 100).toFixed(0)}%</span>
                </div>
                <div class="weight-item">
                    <span>해외</span>
                    <span>${(portfolio.overseas_weight * 100).toFixed(0)}%</span>
                </div>
            </div>
            
            <div class="portfolio-holdings-summary">
                <strong>보유 종목 ${portfolio.total_holdings_count}개</strong>
            </div>

            <div class="portfolio-rationale-preview" style="margin: 12px 0; padding: 12px; background: rgba(59, 130, 246, 0.1); border-left: 3px solid #3b82f6; border-radius: 4px;">
                 <div style="font-size: 0.85rem; color: #1d4ed8; margin-bottom: 4px; font-weight: bold; text-transform: uppercase;">KEY STRATEGY</div>
                 <div style="font-size: 0.9rem; color: #334155; line-height: 1.4;">
                    ${portfolio.explainability && portfolio.explainability.why_this_portfolio && portfolio.explainability.why_this_portfolio.length > 0
            ? portfolio.explainability.why_this_portfolio[0].replace('Logic:', '').replace('Theoretical Basis:', '').trim()
            : portfolio.description}
                 </div>
            </div>
            
            <button class="btn-secondary" onclick="viewPortfolioDetail(${index})">
                자세히 보기
            </button>
        </div>
    `).join('');
}

function viewPortfolioDetail(index) {
    const portfolio = portfoliosResult.portfolios[index];
    const portfolioDetail = document.getElementById('portfolioDetail');
    const exp = portfolio.explainability || {};

    // Move to step 3
    moveToStep(3);

    const detailContainer = document.getElementById('portfolioDetail');

    // Show loading state
    detailContainer.innerHTML = `
        <div class="loading-state" style="padding: 100px 0; text-align: center;">
            <div class="loading-spinner" style="margin: 0 auto 20px;"></div>
            <h3 style="color:#2d3748; margin-bottom:10px;">포트폴리오 상세 분석 중...</h3>
            <p style="color:#64748b;">선택하신 포트폴리오의 세부 구성과 운용 전략을 불러오고 있습니다.</p>
        </div>
    `;

    // Simulate short delay for better UX (and to let the user see the loading screen)
    setTimeout(() => {
        renderPortfolioDetail(portfolio, exp);
    }, 800);
}

function renderPortfolioDetail(portfolio, exp) {
    const portfolioDetail = document.getElementById('portfolioDetail');

    portfolioDetail.innerHTML = `
        <div class="detail-header">
            <button class="btn-back" onclick="moveToStep(2)">← 목록으로 돌아가기</button>
            <h2 class="detail-title">${exp.portfolio_name_fancy || portfolio.name}</h2>
            <p class="detail-description" style="color:#64748b; font-style:italic; font-size:1.1em; margin-top:5px;">"${exp.slogan || portfolio.description}"</p>
            
            ${exp.investment_goal_summary ? `
            <div class="investment-goal-summary" style="margin-top:20px; padding:20px; background:#f8fafc; border-radius:12px; border-left:5px solid #3b82f6; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                <strong style="display:flex; align-items:center; font-size:1.1em; color:#1e3a8a; margin-bottom:8px;">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:8px;"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="12" r="6"></circle><circle cx="12" cy="12" r="2"></circle></svg>
                    투자 목표 요약
                </strong>
                <p style="margin:0; color:#334155; line-height:1.5;">${exp.investment_goal_summary}</p>
            </div>
            ` : ''}
        </div>
        
        <div class="detail-grid">
            <!-- Left: Composition -->
            <div class="detail-section">
                <h3 class="detail-subtitle">포트폴리오 구성</h3>
                
                <div class="asset-allocation-chart">
                    <div style="display: flex; height: 24px; border-radius: 12px; overflow: hidden; margin-bottom: 24px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <div style="width: ${portfolio.domestic_weight * 100}%; background: #3b82f6;" title="국내"></div>
                        <div style="width: ${portfolio.overseas_weight * 100}%; background: #8b5cf6;" title="해외"></div>
                    </div>
                    <div style="display:flex; justify-content:space-between; margin-bottom:20px; font-size:0.9em; color:#475569;">
                        <span><span style="display:inline-block; width:10px; height:10px; background:#3b82f6; border-radius:50%; margin-right:5px;"></span>국내 ${(portfolio.domestic_weight * 100).toFixed(0)}%</span>
                        <span><span style="display:inline-block; width:10px; height:10px; background:#8b5cf6; border-radius:50%; margin-right:5px;"></span>해외 ${(portfolio.overseas_weight * 100).toFixed(0)}%</span>
                    </div>
                </div>
                
                <div class="holdings-list">
                    ${portfolio.holdings.map(holding => `
                        <div class="holding-item" style="padding: 12px; margin-bottom: 8px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fff;">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                                <div>
                                    <div class="holding-name" style="font-weight:600; color:#1e293b;">${holding.name}</div>
                                    <div class="holding-ticker" style="font-size:0.8em; color:#64748b;">${holding.ticker}</div>
                                </div>
                                <div class="holding-weight" style="font-weight:700; color:#2563eb;">${(holding.weight * 100).toFixed(1)}%</div>
                            </div>
                            ${holding.rationale ? `<div style="font-size:0.85em; color:#475569; margin-top:6px; padding-top:6px; border-top:1px dashed #e2e8f0;">${holding.rationale}</div>` : ''}
                        </div>
                    `).join('')}
                </div>
            </div>
            
            <!-- Right: Analysis -->
            <div class="detail-section">
                <h3 class="detail-subtitle">심층 분석 및 운용 가이드</h3>
                
                <!-- 1. Why & Logic -->
                <div class="analysis-card">
                    <h4>선정 근거 및 운용 철학</h4>
                    <ul style="padding-left:20px; color:#334155;">
                        ${exp.why_this_portfolio ? exp.why_this_portfolio.map(text => `<li style="margin-bottom:6px;">${text}</li>`).join('') : '<li>분석 데이터 없음</li>'}
                    </ul>
                </div>
                
                <!-- 2. Risk Summary (4-Grid) -->
                ${exp.risk_summary ? `
                <div class="analysis-card warning">
                    <h4 style="display:flex; align-items:center;">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:8px;"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
                        4대 핵심 리스크 요약
                    </h4>
                    <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px;">
                        <div style="background:rgba(254, 242, 242, 0.7); padding:10px; border-radius:6px; border:1px solid #fecaca;">
                            <strong style="display:block; font-size:0.85em; color:#b91c1c; margin-bottom:4px;">시장 리스크</strong>
                            <p style="font-size:0.8em; color:#450a0a; margin:0; line-height:1.3;">${exp.risk_summary.market}</p>
                        </div>
                        <div style="background:rgba(254, 242, 242, 0.7); padding:10px; border-radius:6px; border:1px solid #fecaca;">
                            <strong style="display:block; font-size:0.85em; color:#b91c1c; margin-bottom:4px;">환율 리스크</strong>
                            <p style="font-size:0.8em; color:#450a0a; margin:0; line-height:1.3;">${exp.risk_summary.currency}</p>
                        </div>
                        <div style="background:rgba(254, 242, 242, 0.7); padding:10px; border-radius:6px; border:1px solid #fecaca;">
                            <strong style="display:block; font-size:0.85em; color:#b91c1c; margin-bottom:4px;">유동성 리스크</strong>
                            <p style="font-size:0.8em; color:#450a0a; margin:0; line-height:1.3;">${exp.risk_summary.liquidity}</p>
                        </div>
                        <div style="background:rgba(254, 242, 242, 0.7); padding:10px; border-radius:6px; border:1px solid #fecaca;">
                            <strong style="display:block; font-size:0.85em; color:#b91c1c; margin-bottom:4px;">전략 리스크</strong>
                            <p style="font-size:0.8em; color:#450a0a; margin:0; line-height:1.3;">${exp.risk_summary.strategy}</p>
                        </div>
                    </div>
                </div>
                ` : ''}

                <!-- 3. Rebalancing Guide -->
                ${exp.rebalancing_guide ? `
                <div class="analysis-card info">
                    <h4 style="display:flex; align-items:center;">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right:8px;"><path d="M2.5 2v6h6M2.66 15.57a10 10 0 1 0 .57-8.38"/></svg>
                        리밸런싱 및 위험 관리 방침
                    </h4>
                    <ul style="list-style:none; padding-left:0; margin:0;">
                        <li style="margin-bottom:10px; display:flex; align-items:flex-start;">
                            <span style="margin-right:8px; margin-top:3px; color:#3b82f6;">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                            </span>
                            <div>
                                <strong style="color:#1d4ed8;">정기 리밸런싱</strong>
                                <div style="font-size:0.9em; color:#334155;">${exp.rebalancing_guide.periodic}</div>
                            </div>
                        </li>
                        <li style="margin-bottom:10px; display:flex; align-items:flex-start;">
                            <span style="margin-right:8px; margin-top:3px; color:#3b82f6;">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path></svg>
                            </span>
                            <div>
                                <strong style="color:#1d4ed8;">위험 관리</strong>
                                <div style="font-size:0.9em; color:#334155;">${exp.rebalancing_guide.risk_control}</div>
                            </div>
                        </li>
                        <li style="margin-bottom:10px; display:flex; align-items:flex-start;">
                            <span style="margin-right:8px; margin-top:3px; color:#3b82f6;">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>
                            </span>
                            <div>
                                <strong style="color:#1d4ed8;">스마트 알림</strong>
                                <div style="font-size:0.9em; color:#334155;">${exp.rebalancing_guide.smart_alert}</div>
                            </div>
                        </li>
                    </ul>
                </div>
                ` : ''}
                
                <div class="analysis-card">
                    <h4>주요 모니터링 지표</h4>
                    <ul style="padding-left:20px; color:#334155;">
                        ${exp.what_to_watch ? exp.what_to_watch.map(text => `<li style="margin-bottom:6px;">${text}</li>`).join('') : ''}
                    </ul>
                </div>
            </div>
        </div>
    `;
}

// ============================================================
// Step Navigation
// ============================================================

function moveToStep(stepNumber) {
    currentFundStep = stepNumber;

    // Update step indicators
    document.querySelectorAll('.fund-step').forEach(step => {
        const stepNum = parseInt(step.dataset.step);
        step.classList.toggle('active', stepNum === stepNumber);
        step.classList.toggle('completed', stepNum < stepNumber);
    });

    // Show correct step content
    document.querySelectorAll('.fund-step-content').forEach(content => {
        const stepNum = parseInt(content.dataset.stepContent);
        content.style.display = stepNum === stepNumber ? 'block' : 'none';
        content.classList.toggle('active', stepNum === stepNumber);
    });
}

function updateFundLoadingStatus(message) {
    const statusElement = document.getElementById('fundLoadingStatus');
    const progressBar = document.getElementById('fundProgressBar');

    if (statusElement) {
        statusElement.textContent = message;

        let progress = 10;
        // Step 감지 및 시퀀스 시작
        if (message.includes("Step 1")) {
            progress = 35;
            startLoadingSequence(1);
        }
        else if (message.includes("Step 2")) {
            progress = 65;
            startLoadingSequence(2);
        }
        else if (message.includes("Step 3")) {
            progress = 95;
            startLoadingSequence(3);
        }

        if (progressBar) {
            progressBar.style.width = `${progress}% `;
        }
    }
}

function startLoadingSequence(step) {
    if (loadingInterval) clearInterval(loadingInterval);

    const messages = LOADING_MESSAGES[step] || [];
    let index = 0;

    const loadingText = document.querySelector('.loading-text');
    if (!loadingText) return;

    // 즉시 첫 메시지 표시
    if (messages.length > 0) loadingText.textContent = messages[0];

    loadingInterval = setInterval(() => {
        index = (index + 1) % messages.length;
        loadingText.textContent = messages[index];
    }, 2500); // 2.5초마다 변경
}

function stopLoadingSequence() {
    if (loadingInterval) {
        clearInterval(loadingInterval);
        loadingInterval = null;
    }
}

// ============================================================
// Export
// ============================================================

window.handleSurveySubmit = handleSurveySubmit;
window.viewPortfolioDetail = viewPortfolioDetail;
window.moveToStep = moveToStep;
