// WigglNet - Interactive Animations & Live Updates

// Number counting animation
function animateCounter(element, target, duration = 2000) {
    const start = 0;
    const increment = target / (duration / 16);
    let current = start;

    const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
            element.textContent = formatNumber(target);
            clearInterval(timer);
        } else {
            element.textContent = formatNumber(Math.floor(current));
        }
    }, 16);
}

// Format large numbers with commas or abbreviations
function formatNumber(num) {
    if (num >= 1000000000) {
        return (num / 1000000000).toFixed(1) + 'B';
    } else if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

// Initialize all counter animations
function initCounters() {
    const counters = document.querySelectorAll('[data-count]');
    counters.forEach(counter => {
        const target = parseInt(counter.getAttribute('data-count'));
        animateCounter(counter, target);
    });
}

// Live feed updates
const liveFeedData = [
    { text: '📱 Mobile accessories surpassed 100K sales', time: 'Just now' },
    { text: '👟 Athletic footwear price index up +15%', time: '1 minute ago' },
    { text: '💄 Beauty & skincare: 2,345 new listings', time: '3 minutes ago' },
    { text: '🎮 Gaming hardware trending index at peak', time: '5 minutes ago' },
    { text: '⌚ Smart watch searches increased +89%', time: '7 minutes ago' },
    { text: '🏠 Home goods reviews exceeded 50K', time: '9 minutes ago' },
    { text: '📚 Education category sentiment: 9.2/10', time: '12 minutes ago' },
    { text: '👗 Fashion sector added 156 merchants', time: '15 minutes ago' }
];

function updateLiveFeed() {
    const feedList = document.getElementById('liveFeed');
    if (!feedList) return;

    // Clear existing items
    feedList.innerHTML = '';

    // Add feed items with animation
    liveFeedData.forEach((item, index) => {
        setTimeout(() => {
            const feedItem = document.createElement('div');
            feedItem.className = 'feed-item';
            feedItem.innerHTML = `
                <div class="feed-text">${item.text}</div>
                <div class="feed-time">${item.time}</div>
            `;
            feedList.appendChild(feedItem);
        }, index * 100);
    });
}

// Duplicate ticker content for infinite scroll
function setupTickerScroll() {
    const tickerContent = document.getElementById('tickerContent');
    if (!tickerContent) return;

    const originalContent = tickerContent.innerHTML;
    tickerContent.innerHTML = originalContent + originalContent;
}

// Search category helper function
function searchCategory(category) {
    const searchInput = document.getElementById('categorySearch');
    if (searchInput) {
        searchInput.value = category;
        performSearch();
    }
}

// Mini chart placeholder animation
function animateMiniChart() {
    const miniChart = document.getElementById('priceIndexChart');
    if (!miniChart) return;

    // Create simple sparkline visualization
    const canvas = document.createElement('canvas');
    canvas.width = miniChart.offsetWidth || 300;
    canvas.height = 60;
    const ctx = canvas.getContext('2d');

    // Generate random data points for demo
    const dataPoints = 20;
    const data = [];
    for (let i = 0; i < dataPoints; i++) {
        data.push(30 + Math.random() * 30);
    }

    // Draw sparkline
    ctx.strokeStyle = '#0abde3';
    ctx.lineWidth = 2;
    ctx.beginPath();

    data.forEach((value, index) => {
        const x = (canvas.width / (dataPoints - 1)) * index;
        const y = canvas.height - (value / 60) * canvas.height;
        if (index === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    });

    ctx.stroke();

    // Fill gradient under line
    ctx.lineTo(canvas.width, canvas.height);
    ctx.lineTo(0, canvas.height);
    ctx.closePath();

    const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height);
    gradient.addColorStop(0, 'rgba(10, 189, 227, 0.15)');
    gradient.addColorStop(1, 'rgba(10, 189, 227, 0)');
    ctx.fillStyle = gradient;
    ctx.fill();

    miniChart.appendChild(canvas);
}

// Activity meter circle animation
function animateActivityMeter() {
    const circle = document.getElementById('activityCircle');
    if (!circle) return;

    // Animate the stroke-dashoffset for the progress circle
    const percentage = 87; // 87% activity
    const circumference = 314; // 2 * PI * 50 (radius)
    const offset = circumference - (percentage / 100) * circumference;

    // Create SVG gradient for the stroke
    const svg = circle.closest('svg');
    const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
    const gradient = document.createElementNS('http://www.w3.org/2000/svg', 'linearGradient');
    gradient.setAttribute('id', 'gradient');
    gradient.setAttribute('x1', '0%');
    gradient.setAttribute('y1', '0%');
    gradient.setAttribute('x2', '100%');
    gradient.setAttribute('y2', '100%');

    const stop1 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
    stop1.setAttribute('offset', '0%');
    stop1.setAttribute('stop-color', '#05c46b');

    const stop2 = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
    stop2.setAttribute('offset', '100%');
    stop2.setAttribute('stop-color', '#0abde3');

    gradient.appendChild(stop1);
    gradient.appendChild(stop2);
    defs.appendChild(gradient);
    svg.insertBefore(defs, svg.firstChild);

    // Animate
    setTimeout(() => {
        circle.style.strokeDashoffset = offset;
    }, 500);
}

// Refresh live data periodically
function startLiveUpdates() {
    // Update counters every 30 seconds
    setInterval(() => {
        initCounters();
    }, 30000);

    // Refresh live feed every 15 seconds
    setInterval(() => {
        // Rotate feed data
        const firstItem = liveFeedData.shift();
        liveFeedData.push(firstItem);
        updateLiveFeed();
    }, 15000);
}

// Animate search on Enter key
function setupSearchListeners() {
    const searchInput = document.getElementById('categorySearch');
    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                performSearch();
            }
        });

        // Add focus animation
        searchInput.addEventListener('focus', () => {
            const wrapper = searchInput.closest('.search-input-wrapper');
            if (wrapper) {
                wrapper.style.borderColor = '#0abde3';
            }
        });

        searchInput.addEventListener('blur', () => {
            const wrapper = searchInput.closest('.search-input-wrapper');
            if (wrapper) {
                wrapper.style.borderColor = '';
            }
        });
    }
}

// Card hover effects
function setupCardAnimations() {
    const cards = document.querySelectorAll('.data-card, .category-item, .quick-link');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-4px)';
        });
        card.addEventListener('mouseleave', function() {
            this.style.transform = '';
        });
    });
}

// Initialize all animations when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Initialize counters
    initCounters();

    // Setup ticker
    setupTickerScroll();

    // Update live feed
    updateLiveFeed();

    // Animate charts
    animateMiniChart();
    animateActivityMeter();

    // Setup search
    setupSearchListeners();

    // Setup card animations
    setupCardAnimations();

    // Start live updates
    startLiveUpdates();

    console.log('🚀 WigglNet animations initialized');
});

// Export functions for use in other scripts
window.searchCategory = searchCategory;
window.animateCounter = animateCounter;
