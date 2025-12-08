// Analytics page specific JavaScript
console.log('>>> ANALYTICS.JS FILE EXECUTED <<<');
const ANALYTICS_API_BASE = 'http://localhost:8000';
let analyticsAgents = [];
let analyticsData = null;

// Initialize analytics
async function initAnalytics() {
    console.log('Analytics page init starting...');
    applyTheme();
    console.log('Theme applied');
    await loadAgentsForAnalytics();
    console.log('Agents loaded, now loading analytics...');
    await loadAnalytics();
    console.log('Analytics loaded');

    // Add event listener for date filter
    document.getElementById('date-filter').addEventListener('change', loadAnalytics);
}

// Apply theme from localStorage (global)
function applyTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
}

// Load agents for dropdown
async function loadAgentsForAnalytics() {
    try {
        const response = await fetch(`${ANALYTICS_API_BASE}/agents`);
        if (response.ok) {
            const data = await response.json();
            analyticsAgents = data.agents || [];
            populateAgentFilter();
        }
    } catch (error) {
        console.error('Failed to load agents:', error);
    }
}

// Populate agent filter dropdown
function populateAgentFilter() {
    const select = document.getElementById('agent-filter');
    analyticsAgents.forEach(agent => {
        const option = document.createElement('option');
        option.value = agent.id;
        option.textContent = agent.name;
        select.appendChild(option);
    });
}

// Get days from filter
function getDaysFromFilter() {
    const filter = document.getElementById('date-filter').value;
    switch (filter) {
        case '7d': return 7;
        case '30d': return 30;
        case '90d': return 90;
        default: return 30;
    }
}

// Load analytics data from real API
async function loadAnalytics() {
    try {
        const days = getDaysFromFilter();
        const agentId = document.getElementById('agent-filter').value;

        // Build query params
        let url = `${ANALYTICS_API_BASE}/analytics?days=${days}`;
        if (agentId && agentId !== 'all') {
            url += `&agent_id=${agentId}`;
        }

        console.log('Fetching analytics from:', url);
        const response = await fetch(url);
        console.log('Analytics response status:', response.status);

        if (!response.ok) {
            throw new Error('Failed to fetch analytics');
        }

        const result = await response.json();
        console.log('Analytics data:', result);

        if (result.success) {
            analyticsData = result.data;
            updateStats();
            updateCharts();
            updateTable();
        }
    } catch (error) {
        console.error('Failed to load analytics:', error);
        // Show empty state
        analyticsData = {
            total_conversations: 0,
            total_messages: 0,
            user_messages: 0,
            assistant_messages: 0,
            active_agents: 0,
            documents_indexed: 0,
            agent_stats: [],
            changes: {
                conversations: { value: 0, direction: 'neutral' },
                messages: { value: 0, direction: 'neutral' }
            }
        };
        updateStats();
        updateCharts();
        updateTable();
    }
}

// Update stat cards
function updateStats() {
    document.getElementById('stat-conversations').textContent = analyticsData.total_conversations.toLocaleString();
    document.getElementById('stat-messages').textContent = analyticsData.total_messages.toLocaleString();
    document.getElementById('stat-agents').textContent = analyticsData.active_agents;
    document.getElementById('stat-documents').textContent = analyticsData.documents_indexed;

    // Update change indicators
    updateChangeIndicator('stat-conversations-change', analyticsData.changes?.conversations);
    updateChangeIndicator('stat-messages-change', analyticsData.changes?.messages);
}

// Update change indicator
function updateChangeIndicator(elementId, change) {
    const element = document.getElementById(elementId);
    if (!element || !change) return;

    const value = change.value || 0;
    const direction = change.direction || 'neutral';

    element.className = `stat-change ${direction}`;

    const icon = direction === 'positive'
        ? '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M7 14l5-5 5 5z"></path></svg>'
        : direction === 'negative'
            ? '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M7 10l5 5 5-5z"></path></svg>'
            : '';

    const prefix = value > 0 ? '+' : '';
    element.innerHTML = `${icon}<span>${prefix}${value}% from last period</span>`;
}

// Update charts
function updateCharts() {
    // Agent usage bar chart
    const barChart = document.getElementById('agent-usage-chart');
    barChart.innerHTML = '';

    const agentStats = analyticsData.agent_stats || [];
    const maxMessages = Math.max(...agentStats.map(a => a.messages), 1);
    const colors = ['blue', 'purple', 'green'];

    if (agentStats.length === 0) {
        barChart.innerHTML = '<div class="empty-state"><p class="empty-state-text">No agent data available yet. Start chatting to see usage statistics.</p></div>';
    } else {
        agentStats.slice(0, 5).forEach((agent, index) => {
            const percentage = (agent.messages / maxMessages) * 100;
            const row = document.createElement('div');
            row.className = 'bar-row';
            row.innerHTML = `
                <span class="bar-label">${agent.agent_name || 'Unknown'}</span>
                <div class="bar-container">
                    <div class="bar-fill ${colors[index % 3]}" style="width: ${Math.max(percentage, 5)}%;">
                        <span class="bar-value">${agent.messages}</span>
                    </div>
                </div>
            `;
            barChart.appendChild(row);
        });
    }

    // Doughnut chart
    const userMessages = analyticsData.user_messages || 0;
    const assistantMessages = analyticsData.assistant_messages || 0;
    const total = userMessages + assistantMessages;
    const userPercent = total > 0 ? (userMessages / total) * 100 : 50;

    const doughnut = document.getElementById('message-type-chart');
    doughnut.style.background = `conic-gradient(var(--primary-blue) 0% ${userPercent}%, #6929c4 ${userPercent}% 100%)`;

    document.getElementById('doughnut-total').textContent = total.toLocaleString();
    document.getElementById('legend-user').textContent = userMessages.toLocaleString();
    document.getElementById('legend-assistant').textContent = assistantMessages.toLocaleString();
}

// Update table
function updateTable() {
    const tbody = document.getElementById('agent-table-body');
    tbody.innerHTML = '';

    const agentStats = analyticsData.agent_stats || [];

    if (agentStats.length === 0) {
        // Show all agents from the dropdown even if no stats
        if (analyticsAgents.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5">
                        <div class="empty-state">
                            <p class="empty-state-title">No agents found</p>
                            <p class="empty-state-text">Create an agent to see analytics</p>
                        </div>
                    </td>
                </tr>
            `;
        } else {
            analyticsAgents.forEach(agent => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>
                        <div class="agent-name-cell">
                            <div class="agent-avatar">${agent.name.charAt(0).toUpperCase()}</div>
                            <span>${agent.name}</span>
                        </div>
                    </td>
                    <td>0</td>
                    <td>0</td>
                    <td>--</td>
                    <td>
                        <span class="status-badge active">
                            <span class="status-dot"></span>
                            Active
                        </span>
                    </td>
                `;
                tbody.appendChild(row);
            });
        }
        return;
    }

    agentStats.forEach(agent => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>
                <div class="agent-name-cell">
                    <div class="agent-avatar">${(agent.agent_name || 'U').charAt(0).toUpperCase()}</div>
                    <span>${agent.agent_name || 'Unknown'}</span>
                </div>
            </td>
            <td>${agent.conversations}</td>
            <td>${agent.messages}</td>
            <td>${agent.avg_response_time || 0}s</td>
            <td>
                <span class="status-badge active">
                    <span class="status-dot"></span>
                    Active
                </span>
            </td>
        `;
        tbody.appendChild(row);
    });
}

// Filter by agent
function filterByAgent() {
    loadAnalytics();
}

// Open profile - redirect to login
function openProfile() {
    window.location.href = 'login.html';
}

// Run init when DOM is ready
console.log('analytics.js loaded, initializing...');
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAnalytics);
} else {
    initAnalytics();
}
