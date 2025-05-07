// Dashboard JavaScript

// Chart configurations
const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: {
        duration: 250
    },
    scales: {
        y: {
            beginAtZero: true,
            max: 100
        }
    },
    plugins: {
        legend: {
            display: true,
            position: 'top'
        }
    }
};

// Initialize charts
let systemMetricsChart = null;
let activityChart = null;

// Initialize WebSocket connection
const ws = new WebSocket(`ws://${window.location.host}/ws/metrics`);

ws.onmessage = (event) => {
    const metrics = JSON.parse(event.data);
    updateDashboard(metrics);
};

ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    updateSystemStatus('error');
};

ws.onclose = () => {
    console.log('WebSocket connection closed');
    updateSystemStatus('disconnected');
    // Try to reconnect after 5 seconds
    setTimeout(() => {
        window.location.reload();
    }, 5000);
};

function updateSystemStatus(status) {
    const statusElement = document.getElementById('system-status');
    const icon = statusElement.querySelector('i');
    
    switch(status) {
        case 'healthy':
            statusElement.className = 'nav-item nav-link text-success';
            icon.className = 'bx bx-pulse';
            break;
        case 'warning':
            statusElement.className = 'nav-item nav-link text-warning';
            icon.className = 'bx bx-error';
            break;
        case 'error':
            statusElement.className = 'nav-item nav-link text-danger';
            icon.className = 'bx bx-x-circle';
            break;
        case 'disconnected':
            statusElement.className = 'nav-item nav-link text-secondary';
            icon.className = 'bx bx-wifi-off';
            break;
    }
}

function updateDashboard(metrics) {
    // Update quick stats
    updateQuickStats(metrics);
    
    // Update agent list
    updateAgentList(metrics.agents);
    
    // Update service list
    updateServiceList(metrics.services);
    
    // Update charts
    updateSystemMetricsChart(metrics);
    updateActivityChart(metrics);
    
    // Update system status
    updateSystemStatus(metrics.system.status);
}

function updateQuickStats(metrics) {
    // Update active agents
    const activeAgents = metrics.agents.filter(a => a.status === 'active').length;
    document.getElementById('active-agents-count').textContent = activeAgents;
    const agentsHealth = (activeAgents / metrics.agents.length) * 100;
    updateProgressBar('agents-health-bar', agentsHealth);
    
    // Update system load
    document.getElementById('system-load').textContent = `${metrics.system.cpu_usage}%`;
    updateProgressBar('system-load-bar', metrics.system.cpu_usage);
    
    // Update memory usage
    document.getElementById('memory-usage').textContent = `${metrics.system.memory_usage}%`;
    updateProgressBar('memory-usage-bar', metrics.system.memory_usage);
    
    // Update active tasks
    document.getElementById('active-tasks').textContent = metrics.tasks.active;
    updateProgressBar('tasks-progress-bar', (metrics.tasks.completed / metrics.tasks.total) * 100);
}

function updateProgressBar(id, value) {
    const bar = document.getElementById(id);
    bar.style.width = `${value}%`;
    bar.setAttribute('aria-valuenow', value);
    
    // Update color based on value
    if (value > 80) {
        bar.className = 'progress-bar bg-danger';
    } else if (value > 60) {
        bar.className = 'progress-bar bg-warning';
    } else {
        bar.className = 'progress-bar bg-success';
    }
}

function updateAgentList(agents) {
    const agentList = document.getElementById('agent-list');
    agentList.innerHTML = agents.map(agent => `
        <div class="list-group-item d-flex justify-content-between align-items-center">
            <div>
                <i class="bx ${getAgentIcon(agent.type)} me-2"></i>
                ${agent.name}
            </div>
            <span class="badge bg-${getStatusColor(agent.status)} rounded-pill">
                ${agent.status}
            </span>
        </div>
    `).join('');
}

function updateServiceList(services) {
    const serviceList = document.getElementById('service-list');
    serviceList.innerHTML = services.map(service => `
        <div class="list-group-item d-flex justify-content-between align-items-center">
            <div>
                <i class="bx ${getServiceIcon(service.type)} me-2"></i>
                ${service.name}
            </div>
            <span class="badge bg-${getStatusColor(service.status)} rounded-pill">
                ${service.status}
            </span>
        </div>
    `).join('');
}

function updateSystemMetricsChart(metrics) {
    const ctx = document.getElementById('system-metrics-chart').getContext('2d');
    
    if (!systemMetricsChart) {
        systemMetricsChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'CPU Usage',
                    data: [],
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1
                }, {
                    label: 'Memory Usage',
                    data: [],
                    borderColor: 'rgb(153, 102, 255)',
                    tension: 0.1
                }]
            },
            options: chartOptions
        });
    }
    
    // Add new data points
    const timestamp = new Date().toLocaleTimeString();
    systemMetricsChart.data.labels.push(timestamp);
    systemMetricsChart.data.datasets[0].data.push(metrics.system.cpu_usage);
    systemMetricsChart.data.datasets[1].data.push(metrics.system.memory_usage);
    
    // Keep only last 20 data points
    if (systemMetricsChart.data.labels.length > 20) {
        systemMetricsChart.data.labels.shift();
        systemMetricsChart.data.datasets.forEach(dataset => dataset.data.shift());
    }
    
    systemMetricsChart.update();
}

function updateActivityChart(metrics) {
    const ctx = document.getElementById('activity-chart').getContext('2d');
    
    if (!activityChart) {
        activityChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Task Activity',
                    data: [],
                    borderColor: 'rgb(255, 99, 132)',
                    tension: 0.1
                }]
            },
            options: chartOptions
        });
    }
    
    // Add new data point
    const timestamp = new Date().toLocaleTimeString();
    activityChart.data.labels.push(timestamp);
    activityChart.data.datasets[0].data.push(metrics.tasks.active);
    
    // Keep only last 60 data points
    if (activityChart.data.labels.length > 60) {
        activityChart.data.labels.shift();
        activityChart.data.datasets[0].data.shift();
    }
    
    activityChart.update();
}

function getAgentIcon(type) {
    const icons = {
        'orchestrator': 'bx-server',
        'manager': 'bx-cog',
        'worker': 'bx-bot',
        'monitor': 'bx-radar',
        default: 'bx-cube'
    };
    return icons[type] || icons.default;
}

function getServiceIcon(type) {
    const icons = {
        'database': 'bx-data',
        'cache': 'bx-memory-card',
        'queue': 'bx-list-ul',
        'api': 'bx-network',
        default: 'bx-cube'
    };
    return icons[type] || icons.default;
}

function getStatusColor(status) {
    const colors = {
        'active': 'success',
        'warning': 'warning',
        'error': 'danger',
        'inactive': 'secondary',
        default: 'primary'
    };
    return colors[status] || colors.default;
}

// Event Listeners
document.getElementById('refresh-agents').addEventListener('click', async () => {
    try {
        const response = await fetch('/agents');
        const data = await response.json();
        updateAgentList(data.agents);
    } catch (error) {
        console.error('Error refreshing agents:', error);
    }
});

document.getElementById('refresh-services').addEventListener('click', async () => {
    try {
        const response = await fetch('/services');
        const data = await response.json();
        updateServiceList(data.services);
    } catch (error) {
        console.error('Error refreshing services:', error);
    }
});

// Time range buttons
document.querySelectorAll('[data-time]').forEach(button => {
    button.addEventListener('click', (e) => {
        // Remove active class from all buttons
        e.target.parentElement.querySelectorAll('button').forEach(btn => {
            btn.classList.remove('active');
        });
        // Add active class to clicked button
        e.target.classList.add('active');
        
        // Update chart time range
        const hours = parseInt(e.target.dataset.time);
        // TODO: Implement time range filtering
    });
}); 