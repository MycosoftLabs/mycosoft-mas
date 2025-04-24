// Dashboard initialization
document.addEventListener('DOMContentLoaded', function() {
    initializeWebSocket();
    initializeCharts();
    initializeEventHandlers();
    refreshDashboard();
});

// WebSocket connection
function initializeWebSocket() {
    ws = new WebSocket(`ws://${window.location.host}/ws`);
    
    ws.onopen = function() {
        console.log('WebSocket connection established');
        updateSystemStatus('Connected');
    };
    
    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);
        updateDashboard(data);
    };
    
    ws.onclose = function() {
        console.log('WebSocket connection closed');
        updateSystemStatus('Disconnected');
        // Attempt to reconnect after 5 seconds
        setTimeout(initializeWebSocket, 5000);
    };
}

// Initialize Charts
function initializeCharts() {
    // Performance Chart
    const perfCtx = document.getElementById('performanceChart').getContext('2d');
    performanceChart = new Chart(perfCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'CPU Usage',
                data: [],
                borderColor: '#2ecc71',
                tension: 0.4
            }, {
                label: 'Memory Usage',
                data: [],
                borderColor: '#3498db',
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100
                }
            }
        }
    });
}

// Event Handlers
function initializeEventHandlers() {
    // Tab navigation
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const tabId = this.getAttribute('data-tab');
            if (tabId) {
                showTab(tabId);
            }
        });
    });
}

// Show selected tab
function showTab(tabId) {
    document.querySelectorAll('.dashboard-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
    });
    
    document.getElementById(tabId).classList.add('active');
    document.querySelector(`[data-tab="${tabId}"]`).classList.add('active');
}

// Refresh dashboard data
function refreshDashboard() {
    fetch('/api/metrics')
        .then(response => response.json())
        .then(data => {
            updateDashboard(data);
        })
        .catch(error => {
            console.error('Error fetching metrics:', error);
        });
}

// Update dashboard with new data
function updateDashboard(data) {
    if (data.metrics) {
        // Update metric cards
        document.getElementById('activeAgentsCount').textContent = data.metrics.agent_count;
        document.getElementById('totalAgentsCount').textContent = data.metrics.total_agents;
        document.getElementById('activeTasksCount').textContent = data.metrics.active_tasks;
        document.getElementById('completedTasksCount').textContent = data.metrics.completed_tasks;
        document.getElementById('knowledgeNodesCount').textContent = data.metrics.knowledge_nodes;
        document.getElementById('knowledgeRelationsCount').textContent = data.metrics.knowledge_relations;
        document.getElementById('systemHealth').textContent = `${data.metrics.system_health}%`;
        document.getElementById('systemUptime').textContent = data.metrics.uptime;
        
        // Update performance chart
        if (performanceChart && data.metrics.performance_data) {
            performanceChart.data.labels = data.metrics.performance_data.labels;
            performanceChart.data.datasets[0].data = data.metrics.performance_data.cpu;
            performanceChart.data.datasets[1].data = data.metrics.performance_data.memory;
            performanceChart.update();
        }
    }
}

// Update system status indicator
function updateSystemStatus(status) {
    const statusElement = document.getElementById('systemStatus');
    statusElement.textContent = status;
    
    if (status === 'Connected') {
        statusElement.classList.remove('text-danger');
        statusElement.classList.add('text-success');
    } else {
        statusElement.classList.remove('text-success');
        statusElement.classList.add('text-danger');
    }
}

// Utility function to format dates
function formatDate(date) {
    return moment(date).format('YYYY-MM-DD HH:mm:ss');
}

// Refresh dashboard every 30 seconds
setInterval(refreshDashboard, 30000); 