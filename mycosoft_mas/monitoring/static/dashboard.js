// Dashboard WebSocket Connection
let ws = null;
let performanceChart = null;
let systemMetricsChart = null;
let resourceUsageChart = null;
let knowledgeNetwork = null;

// Initialize WebSocket connection
function initializeWebSocket() {
    ws = new WebSocket(`ws://${window.location.host}/ws`);
    
    ws.onopen = () => {
        console.log('WebSocket connected');
        updateSystemStatus('Connected');
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        updateDashboard(data);
    };
    
    ws.onclose = () => {
        console.log('WebSocket disconnected');
        updateSystemStatus('Disconnected');
        setTimeout(initializeWebSocket, 5000);
    };
}

// Update dashboard with new data
function updateDashboard(data) {
    // Update metrics
    document.getElementById('activeAgentsCount').textContent = data.metrics.agent_count;
    document.getElementById('totalAgentsCount').textContent = data.metrics.total_agents;
    document.getElementById('activeTasksCount').textContent = data.metrics.active_tasks;
    document.getElementById('completedTasksCount').textContent = data.metrics.completed_tasks;
    document.getElementById('knowledgeNodesCount').textContent = data.metrics.knowledge_nodes;
    document.getElementById('knowledgeRelationsCount').textContent = data.metrics.knowledge_relations;
    document.getElementById('systemHealth').textContent = `${data.metrics.system_health}%`;
    document.getElementById('systemUptime').textContent = data.metrics.uptime;

    // Update performance chart
    updatePerformanceChart(data.metrics.performance_data);
    
    // Update agent status table
    updateAgentTable(data.agents);
    
    // Update task table
    updateTaskTable(data.tasks);
    
    // Update knowledge graph
    if (data.knowledge_graph) {
        updateKnowledgeGraph(data.knowledge_graph);
    }
    
    // Update system metrics
    updateSystemMetrics(data.metrics.system_metrics);
}

// Initialize charts
function initializeCharts() {
    // Performance Chart
    const perfCtx = document.getElementById('performanceChart').getContext('2d');
    performanceChart = new Chart(perfCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [
                {
                    label: 'CPU Usage',
                    data: [],
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1
                },
                {
                    label: 'Memory Usage',
                    data: [],
                    borderColor: 'rgb(255, 99, 132)',
                    tension: 0.1
                }
            ]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100
                }
            }
        }
    });

    // System Metrics Chart
    const sysCtx = document.getElementById('systemMetricsChart').getContext('2d');
    systemMetricsChart = new Chart(sysCtx, {
        type: 'bar',
        data: {
            labels: ['Tasks', 'Errors', 'API Calls'],
            datasets: [{
                data: [0, 0, 0],
                backgroundColor: [
                    'rgba(75, 192, 192, 0.2)',
                    'rgba(255, 99, 132, 0.2)',
                    'rgba(54, 162, 235, 0.2)'
                ],
                borderColor: [
                    'rgb(75, 192, 192)',
                    'rgb(255, 99, 132)',
                    'rgb(54, 162, 235)'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Initialize knowledge graph visualization
function initializeKnowledgeGraph() {
    const container = document.getElementById('knowledgeGraph');
    const options = {
        nodes: {
            shape: 'dot',
            size: 16
        },
        physics: {
            forceAtlas2Based: {
                gravitationalConstant: -26,
                centralGravity: 0.005,
                springLength: 230,
                springConstant: 0.18
            },
            maxVelocity: 146,
            solver: 'forceAtlas2Based',
            timestep: 0.35,
            stabilization: { iterations: 150 }
        }
    };
    
    knowledgeNetwork = new vis.Network(container, { nodes: [], edges: [] }, options);
}

// Update functions
function updatePerformanceChart(data) {
    if (performanceChart) {
        performanceChart.data.labels = data.labels;
        performanceChart.data.datasets[0].data = data.cpu;
        performanceChart.data.datasets[1].data = data.memory;
        performanceChart.update();
    }
}

function updateSystemMetrics(metrics) {
    if (systemMetricsChart) {
        systemMetricsChart.data.datasets[0].data = [
            metrics.tasks,
            metrics.errors,
            metrics.api_calls
        ];
        systemMetricsChart.update();
    }
}

function updateKnowledgeGraph(data) {
    if (knowledgeNetwork) {
        knowledgeNetwork.setData({
            nodes: new vis.DataSet(data.nodes),
            edges: new vis.DataSet(data.edges)
        });
    }
}

function updateAgentTable(agents) {
    const tbody = document.getElementById('agentStatusTable');
    tbody.innerHTML = '';
    
    agents.forEach(agent => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${agent.name}</td>
            <td><span class="badge bg-${agent.status === 'active' ? 'success' : 'warning'}">${agent.status}</span></td>
            <td>${agent.tasks}</td>
            <td>${agent.cpu}%</td>
            <td>${agent.memory}%</td>
            <td>${moment(agent.last_active).fromNow()}</td>
            <td>
                <button class="btn btn-sm btn-primary" onclick="restartAgent('${agent.id}')">
                    <i class="fa fa-refresh"></i>
                </button>
                <button class="btn btn-sm btn-info" onclick="viewAgentLogs('${agent.id}')">
                    <i class="fa fa-file-text"></i>
                </button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function updateTaskTable(tasks) {
    const tbody = document.getElementById('taskTable');
    tbody.innerHTML = '';
    
    tasks.forEach(task => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${task.id}</td>
            <td>${task.type}</td>
            <td><span class="badge bg-${task.status === 'running' ? 'primary' : task.status === 'completed' ? 'success' : 'danger'}">${task.status}</span></td>
            <td>${task.agent}</td>
            <td>
                <div class="progress">
                    <div class="progress-bar" role="progressbar" style="width: ${task.progress}%" aria-valuenow="${task.progress}" aria-valuemin="0" aria-valuemax="100">${task.progress}%</div>
                </div>
            </td>
            <td>${moment(task.start_time).format('YYYY-MM-DD HH:mm:ss')}</td>
            <td>
                <button class="btn btn-sm btn-danger" onclick="cancelTask('${task.id}')" ${task.status !== 'running' ? 'disabled' : ''}>
                    <i class="fa fa-times"></i>
                </button>
                <button class="btn btn-sm btn-info" onclick="viewTaskDetails('${task.id}')">
                    <i class="fa fa-info-circle"></i>
                </button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// Action handlers
async function restartAgent(agentId) {
    try {
        const response = await fetch(`/api/agents/${agentId}/restart`, {
            method: 'POST'
        });
        const data = await response.json();
        if (data.status === 'success') {
            showNotification('Agent restart initiated', 'success');
        } else {
            showNotification('Failed to restart agent', 'error');
        }
    } catch (error) {
        console.error('Error restarting agent:', error);
        showNotification('Error restarting agent', 'error');
    }
}

async function cancelTask(taskId) {
    try {
        const response = await fetch(`/api/tasks/${taskId}/cancel`, {
            method: 'POST'
        });
        const data = await response.json();
        if (data.status === 'success') {
            showNotification('Task cancelled successfully', 'success');
        } else {
            showNotification('Failed to cancel task', 'error');
        }
    } catch (error) {
        console.error('Error cancelling task:', error);
        showNotification('Error cancelling task', 'error');
    }
}

// Utility functions
function showNotification(message, type) {
    // Implementation depends on your preferred notification library
    console.log(`${type}: ${message}`);
}

function updateSystemStatus(status) {
    const statusElement = document.getElementById('systemStatus');
    statusElement.textContent = status;
    statusElement.className = status === 'Connected' ? 'text-success' : 'text-danger';
}

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    initializeCharts();
    initializeKnowledgeGraph();
    initializeWebSocket();
    
    // Handle tab switching
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const tabId = e.target.getAttribute('data-tab');
            if (tabId) {
                document.querySelectorAll('.dashboard-tab').forEach(tab => {
                    tab.classList.remove('active');
                });
                document.getElementById(tabId).classList.add('active');
                
                document.querySelectorAll('.nav-link').forEach(navLink => {
                    navLink.classList.remove('active');
                });
                e.target.classList.add('active');
            }
        });
    });
}); 