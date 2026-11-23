/**
 * Side Menu - JavaScript
 * 
 * 통합 사이드 메뉴 (챗봇 + 급등주)
 */

document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const sideMenuToggle = document.getElementById('sideMenuToggle');
    const sideMenu = document.getElementById('sideMenu');
    const sideMenuClose = document.getElementById('sideMenuClose');
    const sideMenuTabs = document.querySelectorAll('.side-menu-tab');
    const sideMenuContents = document.querySelectorAll('.side-menu-content');

    // Create overlay
    const overlay = document.createElement('div');
    overlay.className = 'side-menu-overlay';
    document.body.appendChild(overlay);

    // Open side menu
    if (sideMenuToggle) {
        sideMenuToggle.addEventListener('click', () => {
            sideMenu.classList.add('active');
            overlay.classList.add('active');
        });
    }

    // Close side menu
    function closeSideMenu() {
        sideMenu.classList.remove('active');
        overlay.classList.remove('active');
    }

    if (sideMenuClose) {
        sideMenuClose.addEventListener('click', closeSideMenu);
    }

    overlay.addEventListener('click', closeSideMenu);

    // Load Hot Stocks Data Function
    async function loadHotStocksData() {
        const hotStocksList = document.getElementById('sideHotStocksList');

        if (!hotStocksList) return;

        // Show loading state if empty
        if (hotStocksList.children.length <= 1) {
            hotStocksList.innerHTML = '<div class="hot-stock-item"><div class="hot-stock-name">로딩 중...</div></div>';
        }

        try {
            const response = await fetch('/api/hot-stocks');
            const data = await response.json();

            if (data.hot_stocks && data.hot_stocks.length > 0) {
                hotStocksList.innerHTML = data.hot_stocks.map((stock, index) => `
                    <div class="hot-stock-item" onclick="analyzeStock('${stock.ticker}')">
                        <div class="hot-stock-rank">${index + 1}</div>
                        <div class="hot-stock-info">
                            <div class="hot-stock-name">${stock.name}</div>
                            <div class="hot-stock-ticker">${stock.ticker}</div>
                        </div>
                        <div class="hot-stock-change ${(stock.change_pct || 0) > 0 ? 'positive' : 'negative'}">
                            ${(stock.change_pct || 0) > 0 ? '+' : ''}${(stock.change_pct || 0).toFixed(2)}%
                        </div>
                    </div>
                `).join('');
            } else {
                hotStocksList.innerHTML = '<div class="hot-stock-item"><div class="hot-stock-name">데이터 없음</div></div>';
            }
        } catch (error) {
            console.error('Failed to load hot stocks:', error);
            hotStocksList.innerHTML = '<div class="hot-stock-item"><div class="hot-stock-name">로딩 실패</div></div>';
        }
    }

    // Tab switching
    sideMenuTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.sideTab;

            // Remove active from all tabs
            sideMenuTabs.forEach(t => t.classList.remove('active'));
            sideMenuContents.forEach(c => c.classList.remove('active'));

            // Add active to clicked tab
            tab.classList.add('active');

            // Show corresponding content
            const content = document.querySelector(`[data-side-content="${tabName}"]`);
            if (content) {
                content.classList.add('active');
            }

            // Load data if hot-stocks tab
            if (tabName === 'hot-stocks') {
                loadHotStocksData();
            }
        });
    });

    // Load hot stocks when opening if tab is active
    if (sideMenuToggle) {
        sideMenuToggle.addEventListener('click', () => {
            const activeTab = document.querySelector('.side-menu-tab.active');
            if (activeTab && activeTab.dataset.sideTab === 'hot-stocks') {
                loadHotStocksData();
            }
        });
    }
});

// Analyze stock function
function analyzeStock(ticker) {
    // Switch to analytics tab
    const analyticsTab = document.querySelector('[data-tab="analytics"]');
    if (analyticsTab) {
        analyticsTab.click();
    }

    // Trigger search
    const searchInput = document.getElementById('stockSearch');
    if (searchInput) {
        searchInput.value = ticker;
        searchInput.dispatchEvent(new Event('input'));
    }

    // Close side menu
    document.querySelector('.side-menu-overlay')?.click();
}

window.analyzeStock = analyzeStock;
