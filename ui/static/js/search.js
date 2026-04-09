/**
 * WigglNet Search and Results Handler
 */

// Perform search
async function performSearch() {
    const searchInput = document.getElementById('categorySearch');
    const searchTerm = searchInput.value.trim();

    if (!searchTerm) {
        alert('Please enter a keyword or category');
        return;
    }

    // Hide hero, show results
    document.querySelector('.hero-search').classList.add('hidden');
    document.getElementById('resultsPage').classList.remove('hidden');
    document.getElementById('searchedTerm').textContent = searchTerm;

    // Fetch and display results
    await loadResults(searchTerm);
}

// Back to search
function backToSearch() {
    document.querySelector('.hero-search').classList.remove('hidden');
    document.getElementById('resultsPage').classList.add('hidden');
}

// Load results data
async function loadResults(searchTerm) {
    try {
        // Fetch keyword data
        const response = await fetch(`/api/search?q=${encodeURIComponent(searchTerm)}`);
        const data = await response.json();

        // Render sentiment word cloud
        renderSentimentCloud(data.sentimentWords || []);

        // Render price chart
        renderPriceChart(data.priceHistory || []);

        // Render CPI charts
        renderCPIChart(data.cpiData || []);
        renderTrendsChart(data.trendsData || []);

        // Render data table
        renderResultsTable(data.tableData || []);

    } catch (error) {
        console.error('Error loading results:', error);
        alert('Error loading search results');
    }
}

// Render sentiment word cloud
function renderSentimentCloud(words) {
    const canvas = document.getElementById('sentimentCloud');
    const ctx = canvas.getContext('2d');

    // Clear canvas
    ctx.fillStyle = '#fafaf8';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    if (words.length === 0) {
        ctx.fillStyle = '#999';
        ctx.font = '16px Inter';
        ctx.textAlign = 'center';
        ctx.fillText('No sentiment data available', canvas.width / 2, canvas.height / 2);
        return;
    }

    // Simple word cloud layout
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;

    words.forEach((word, i) => {
        const angle = (i / words.length) * Math.PI * 2;
        const radius = 80 + (i % 3) * 60;
        const x = centerX + Math.cos(angle) * radius;
        const y = centerY + Math.sin(angle) * radius;

        const fontSize = 14 + (word.weight / 10);
        ctx.font = `${fontSize}px Inter`;
        ctx.textAlign = 'center';
        ctx.fillStyle = word.sentiment === 'positive' ? '#00aa44' :
                       word.sentiment === 'negative' ? '#dd3333' : '#666';
        ctx.fillText(word.text, x, y);
    });
}

// Render price chart
function renderPriceChart(priceData) {
    const canvas = document.getElementById('priceChart');
    const ctx = canvas.getContext('2d');

    // Clear canvas
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    if (priceData.length === 0) {
        ctx.fillStyle = '#999';
        ctx.font = '16px Inter';
        ctx.textAlign = 'center';
        ctx.fillText('No price data available', canvas.width / 2, canvas.height / 2);
        return;
    }

    // Draw simple line chart
    const padding = 50;
    const chartWidth = canvas.width - padding * 2;
    const chartHeight = canvas.height - padding * 2;

    // Find min/max
    const prices = priceData.map(d => d.price);
    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);
    const priceRange = maxPrice - minPrice || 1;

    // Draw axes
    ctx.strokeStyle = '#e0e0dd';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(padding, padding);
    ctx.lineTo(padding, canvas.height - padding);
    ctx.lineTo(canvas.width - padding, canvas.height - padding);
    ctx.stroke();

    // Draw line
    ctx.strokeStyle = '#1a1a1a';
    ctx.lineWidth = 3;
    ctx.beginPath();

    priceData.forEach((point, i) => {
        const x = padding + (i / (priceData.length - 1)) * chartWidth;
        const y = canvas.height - padding - ((point.price - minPrice) / priceRange) * chartHeight;

        if (i === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    });

    ctx.stroke();

    // Labels
    ctx.fillStyle = '#666';
    ctx.font = '12px Inter';
    ctx.textAlign = 'left';
    ctx.fillText(`$${minPrice.toFixed(2)}`, 5, canvas.height - padding + 5);
    ctx.fillText(`$${maxPrice.toFixed(2)}`, 5, padding + 15);
}

// Render CPI chart
function renderCPIChart(cpiData) {
    const canvas = document.getElementById('cpiChart');
    const ctx = canvas.getContext('2d');

    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    if (cpiData.length === 0) {
        ctx.fillStyle = '#999';
        ctx.font = '14px Inter';
        ctx.textAlign = 'center';
        ctx.fillText('No CPI data', canvas.width / 2, canvas.height / 2);
        return;
    }

    // Simple bar chart
    const barWidth = canvas.width / cpiData.length - 10;
    const maxValue = Math.max(...cpiData.map(d => d.value));

    cpiData.forEach((item, i) => {
        const barHeight = (item.value / maxValue) * (canvas.height - 40);
        const x = i * (barWidth + 10) + 10;
        const y = canvas.height - barHeight - 20;

        ctx.fillStyle = '#1a1a1a';
        ctx.fillRect(x, y, barWidth, barHeight);

        ctx.fillStyle = '#666';
        ctx.font = '10px Inter';
        ctx.textAlign = 'center';
        ctx.fillText(item.label, x + barWidth / 2, canvas.height - 5);
    });
}

// Render trends chart
function renderTrendsChart(trendsData) {
    const canvas = document.getElementById('trendsChart');
    const ctx = canvas.getContext('2d');

    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    if (trendsData.length === 0) {
        ctx.fillStyle = '#999';
        ctx.font = '14px Inter';
        ctx.textAlign = 'center';
        ctx.fillText('No trends data', canvas.width / 2, canvas.height / 2);
        return;
    }

    // Similar to CPI chart
    const barWidth = canvas.width / trendsData.length - 10;
    const maxValue = Math.max(...trendsData.map(d => d.interest));

    trendsData.forEach((item, i) => {
        const barHeight = (item.interest / maxValue) * (canvas.height - 40);
        const x = i * (barWidth + 10) + 10;
        const y = canvas.height - barHeight - 20;

        ctx.fillStyle = '#0066ff';
        ctx.fillRect(x, y, barWidth, barHeight);

        ctx.fillStyle = '#666';
        ctx.font = '10px Inter';
        ctx.textAlign = 'center';
        ctx.fillText(item.keyword.substring(0, 8), x + barWidth / 2, canvas.height - 5);
    });
}

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
