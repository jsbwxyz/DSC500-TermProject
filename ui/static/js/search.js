/**
 * WigglNet Search and Results Handler
 */

// Perform search
async function performSearch() {
    const searchInput = document.getElementById('categorySearch');
    const searchTerm = searchInput.value.trim();

    if (!searchTerm) {
        alert('请输入关键词 Please enter a keyword or category');
        return;
    }

    // Hide main content, show results
    document.querySelector('.main-content').classList.add('hidden');
    document.querySelector('.top-nav').style.display = 'block';
    document.querySelector('.ticker-bar').style.display = 'none';
    document.getElementById('resultsPage').classList.remove('hidden');
    document.getElementById('resultsPage').classList.add('active');
    document.getElementById('searchedTerm').textContent = searchTerm;

    // Fetch and display results
    await loadResults(searchTerm);
}

// Back to search
function backToSearch() {
    document.querySelector('.main-content').classList.remove('hidden');
    document.querySelector('.ticker-bar').style.display = 'flex';
    document.getElementById('resultsPage').classList.remove('active');
    document.getElementById('resultsPage').classList.add('hidden');
}

// Load results data
async function loadResults(searchTerm) {
    try {
        // Load matplotlib-generated charts
        loadSentimentChart(searchTerm);
        loadPriceChart(searchTerm);
        loadCPIChart(searchTerm);
        loadTrendsChart(searchTerm);

        // Fetch table data
        const response = await fetch(`/api/search?q=${encodeURIComponent(searchTerm)}`);
        const data = await response.json();

        // Render data table
        renderResultsTable(data.tableData || []);

    } catch (error) {
        console.error('Error loading results:', error);
        alert('Error loading search results');
    }
}

// Load matplotlib-generated charts as images
function loadSentimentChart(searchTerm) {
    const img = document.getElementById('sentimentCloud');
    img.src = `/api/chart/sentiment/${encodeURIComponent(searchTerm)}?t=${Date.now()}`;
    img.onerror = () => {
        console.error('Failed to load sentiment chart');
    };
}

function loadPriceChart(searchTerm) {
    const img = document.getElementById('priceChart');
    img.src = `/api/chart/price/${encodeURIComponent(searchTerm)}?animated=true&t=${Date.now()}`;
    img.onerror = () => {
        console.error('Failed to load price chart');
    };
}

function loadCPIChart(searchTerm) {
    const img = document.getElementById('cpiChart');
    img.src = `/api/chart/cpi/${encodeURIComponent(searchTerm)}?animated=true&t=${Date.now()}`;
    img.onerror = () => {
        console.error('Failed to load CPI chart');
    };
}

function loadTrendsChart(searchTerm) {
    const img = document.getElementById('trendsChart');
    img.src = `/api/chart/trends/${encodeURIComponent(searchTerm)}?animated=true&t=${Date.now()}`;
    img.onerror = () => {
        console.error('Failed to load trends chart');
    };
}

// Old canvas rendering functions removed - now using matplotlib-generated images

// Render results table
function renderResultsTable(tableData) {
    const tbody = document.getElementById('resultsTableBody');
    tbody.innerHTML = '';

    if (tableData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 2rem; color: #999;">No data available</td></tr>';
        return;
    }

    tableData.forEach(row => {
        const tr = document.createElement('tr');

        const sentimentClass = row.sentiment === 'positive' ? 'sentiment-positive' :
                              row.sentiment === 'negative' ? 'sentiment-negative' :
                              'sentiment-neutral';

        tr.innerHTML = `
            <td>${row.val || '-'}</td>
            <td>${row.keyword || '-'}</td>
            <td>${row.product || '-'}</td>
            <td class="${sentimentClass}">${row.sentiment || 'neutral'}</td>
            <td>${row.confidence ? (row.confidence * 100).toFixed(1) + '%' : '-'}</td>
        `;

        tbody.appendChild(tr);
    });
}

// Handle Enter key in search
document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('categorySearch');
    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                performSearch();
            }
        });
    }
});
