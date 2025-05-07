// Dashboard WebSocket Connection
let ws = null;
let performanceChart = null;
let systemMetricsChart = null;
let resourceUsageChart = null;
let knowledgeNetwork = null;

// MYCA Notifications buffer
let mycaNotifications = [];
const MAX_MYCA_NOTIFICATIONS = 20;

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

    // Handle MYCA notifications/events
    if (data.notification || data.event || data.myca_notification) {
        const notif = data.notification || data.event || data.myca_notification;
        addMycaNotification(notif);
    }
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

// Escalation: play sound and highlight for critical notifications
function escalateCriticalNotification() {
    // Play sound
    const audio = new Audio('/dashboard/static/alert.mp3');
    audio.play();
    // Highlight
    const ul = document.getElementById('mycaNotifications');
    if (ul && ul.firstChild) {
        ul.firstChild.classList.add('bg-danger', 'text-white');
        setTimeout(() => {
            ul.firstChild.classList.remove('bg-danger', 'text-white');
        }, 3000);
    }
}

// Batching logic
let notificationBatch = {};
function addMycaNotification(notif) {
    if (!notif) return;
    // Batching: key by agent+type
    const key = `${notif.agent_id || ''}_${notif.event_type || ''}`;
    const now = Date.now();
    if (!notificationBatch[key]) notificationBatch[key] = [];
    notificationBatch[key].push(now);
    // Remove old timestamps
    notificationBatch[key] = notificationBatch[key].filter(ts => now - ts < 60000);
    if (notificationBatch[key].length >= 3) {
        // Batch into a summary notification
        mycaNotifications.unshift({
            message: `(${notificationBatch[key].length}) ${notif.event_type || 'event'}s from ${notif.agent_name || 'agent'} in the last minute`,
            channel: notif.channel || 'dashboard',
            priority: notif.priority === 'critical' ? 'critical' : 'high',
            agent_id: notif.agent_id || '',
            agent_name: notif.agent_name || '',
            event_type: notif.event_type || '',
            context: notif.context || {},
            timestamp: new Date().toISOString()
        });
        notificationBatch[key] = [];
    } else {
        mycaNotifications.unshift({
            message: notif.message || notif,
            channel: notif.channel || 'dashboard',
            priority: notif.priority || 'normal',
            agent_id: notif.agent_id || '',
            agent_name: notif.agent_name || '',
            event_type: notif.event_type || '',
            context: notif.context || {},
            timestamp: notif.timestamp || new Date().toISOString()
        });
    }
    if (mycaNotifications.length > MAX_MYCA_NOTIFICATIONS) {
        mycaNotifications = mycaNotifications.slice(0, MAX_MYCA_NOTIFICATIONS);
    }
    renderMycaNotifications();
    // Escalate if critical
    if (notif.priority === 'critical') escalateCriticalNotification();
}

// Add filter input above notifications panel on DOMContentLoaded
function addMycaNotificationFilter() {
    const notifPanel = document.getElementById('mycaNotifications');
    if (!notifPanel) return;
    if (document.getElementById('mycaNotificationFilter')) return;
    const filterDiv = document.createElement('div');
    filterDiv.className = 'mb-2';
    filterDiv.innerHTML = '<input type="text" id="mycaNotificationFilter" class="form-control form-control-sm" placeholder="Filter notifications...">';
    notifPanel.parentNode.insertBefore(filterDiv, notifPanel);
    document.getElementById('mycaNotificationFilter').addEventListener('input', function() {
        renderMycaNotifications(this.value);
    });
}

function renderMycaNotifications(filter = '') {
    const ul = document.getElementById('mycaNotifications');
    if (!ul) return;
    ul.innerHTML = '';
    mycaNotifications
        .filter(n => !filter || n.message.toLowerCase().includes(filter.toLowerCase()) || n.agent_name.toLowerCase().includes(filter.toLowerCase()) || n.event_type.toLowerCase().includes(filter.toLowerCase()))
        .forEach((n, idx) => {
            let icon = '<i class="fa fa-info-circle"></i>';
            if (n.event_type === 'error') icon = '<i class="fa fa-exclamation-triangle text-danger"></i>';
            else if (n.event_type === 'success') icon = '<i class="fa fa-check-circle text-success"></i>';
            else if (n.event_type === 'warning') icon = '<i class="fa fa-exclamation-circle text-warning"></i>';
            else if (n.event_type === 'critical') icon = '<i class="fa fa-bomb text-danger"></i>';
            else if (n.event_type === 'task') icon = '<i class="fa fa-tasks text-primary"></i>';
            const li = document.createElement('li');
            li.className = `list-group-item list-group-item-${n.priority === 'critical' ? 'danger' : n.priority === 'high' ? 'warning' : 'info'}`;
            li.innerHTML = `
                ${icon} <strong>${n.agent_name ? '[' + n.agent_name + ']' : ''}</strong> ${n.message}
                <span class="badge bg-secondary ms-2">${n.event_type || 'event'}</span>
                <button class="btn btn-sm btn-outline-info float-end ms-2" onclick="showMycaNotificationDetails(${idx})"><i class="fa fa-info"></i></button>
                <span class="float-end text-muted" style="font-size:0.85em;">${new Date(n.timestamp).toLocaleTimeString()}</span>
            `;
            ul.appendChild(li);
        });
}

function showMycaNotificationDetails(idx) {
    const n = mycaNotifications[idx];
    const modal = new bootstrap.Modal(document.getElementById('mycaNotificationModal'));
    const body = document.getElementById('mycaNotificationModalBody');
    body.innerHTML = `
        <div><strong>Agent:</strong> ${n.agent_name || ''} <span class="text-muted">(${n.agent_id || ''})</span></div>
        <div><strong>Type:</strong> <span class="badge bg-secondary">${n.event_type || 'event'}</span></div>
        <div><strong>Message:</strong> ${n.message}</div>
        <div><strong>Channel:</strong> ${n.channel}</div>
        <div><strong>Priority:</strong> ${n.priority}</div>
        <div><strong>Timestamp:</strong> ${new Date(n.timestamp).toLocaleString()}</div>
        <div><strong>Context:</strong><pre style="background:#f8f9fa; padding:8px;">${JSON.stringify(n.context, null, 2)}</pre></div>
    `;
    // Wire up replay button
    const replayBtn = document.getElementById('replayMycaNotificationBtn');
    replayBtn.onclick = function() {
        if ('speechSynthesis' in window) {
            const utter = new SpeechSynthesisUtterance(`${n.agent_name ? n.agent_name + ': ' : ''}${n.message}`);
            utter.rate = 1.0;
            utter.pitch = 1.1;
            utter.lang = 'en-US';
            window.speechSynthesis.speak(utter);
        } else {
            alert('Speech synthesis not supported in this browser.');
        }
    };
    modal.show();
}

// Add MYCA chat input below notifications panel
function addMycaChatInput() {
    const notifPanel = document.getElementById('mycaNotifications');
    if (!notifPanel) return;
    if (document.getElementById('mycaChatInput')) return;
    const chatDiv = document.createElement('div');
    chatDiv.className = 'mt-2';
    chatDiv.innerHTML = `
        <div class="input-group">
            <input type="text" id="mycaChatInput" class="form-control form-control-sm" placeholder="Ask MYCA... (coming soon)">
            <button class="btn btn-primary btn-sm" id="mycaChatSendBtn" disabled><i class="fa fa-paper-plane"></i></button>
        </div>
    `;
    notifPanel.parentNode.appendChild(chatDiv);
}

// Patch DOMContentLoaded to add filter and chat input
const origDOMContentLoaded = document.addEventListener;
document.addEventListener = function(type, fn) {
    if (type === 'DOMContentLoaded') {
        origDOMContentLoaded.call(document, type, function() {
            fn();
            addMycaNotificationFilter();
            addMycaChatInput();
        });
    } else {
        origDOMContentLoaded.call(document, type, fn);
    }
};

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