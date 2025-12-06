// Load agents from LocalStorage (shared with index.html)
let agents = JSON.parse(localStorage.getItem('mcp_agents')) || {
    "agent_default": {
        id: "agent_default",
        name: "My First Agent",
        description: "A helpful AI assistant ready to be configured.",
        system_prompt: "You are a helpful AI assistant."
    }
};

let currentAgentId = null;
let chatHistory = [];

function toggleSidebar() {
    document.getElementById('main-nav').classList.toggle('open');
    document.getElementById('sidebar-overlay').classList.toggle('show');
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    renderAgentList();

    // Check URL params
    const urlParams = new URLSearchParams(window.location.search);
    const mode = urlParams.get('mode');
    const agentId = urlParams.get('agent');

    if (mode === 'create') {
        initCreateMode();
    } else if (agentId && agents[agentId]) {
        selectAgent(agentId);
    } else {
        // Default to first agent if none specified
        const firstId = Object.keys(agents)[0];
        if (firstId) selectAgent(firstId);
    }
});

function initCreateMode() {
    currentAgentId = null; // No ID yet

    // Clear Config Panel
    document.getElementById('agent-name-header').value = ""; // Updated ID
    document.getElementById('agent-desc').value = "";
    document.getElementById('agent-prompt').value = "";

    // Reset Chat to Empty
    document.getElementById('chat-header-name').innerText = "New Agent";
    document.getElementById('chat-history').innerHTML = `
        <div class="empty-state">
            Configure your new agent and click Save to create it.
        </div>
    `;

    // Disable Chat Input until saved
    document.getElementById('user-input').disabled = true;
    document.getElementById('send-btn').disabled = true;
}

function renderAgentList() {
    const list = document.getElementById('agent-list');
    list.innerHTML = '';

    // Add "Back to Dashboard" link
    const backLink = document.createElement('div');
    backLink.className = 'back-link';
    backLink.innerHTML = '<span>←</span> Back to Dashboard';
    backLink.onclick = () => window.location.href = 'index.html';
    list.appendChild(backLink);

    Object.values(agents).forEach(agent => {
        const item = document.createElement('div');
        item.className = `agent-item ${currentAgentId === agent.id ? 'active' : ''}`;
        item.onclick = () => selectAgent(agent.id);
        item.innerHTML = `${agent.name}`; // Removed emoji
        list.appendChild(item);
    });
}

function focusNameInput() {
    document.getElementById('agent-name-header').focus();
}

function saveNameFromHeader() {
    // Optional: Auto-save when clicking away from name
    // saveAgentConfig(); 
}

function handleNameKeyPress(event) {
    if (event.key === 'Enter') {
        event.preventDefault(); // Prevent default form submission if any
        document.getElementById('agent-name-header').blur(); // Remove focus
        saveAgentConfig(); // Trigger save
    }
}

function selectAgent(id) {
    currentAgentId = id;
    const agent = agents[id];

    // Update Sidebar UI (Orchestrator only)
    renderAgentList();

    // Populate Config Panel (if elements exist)
    const nameHeader = document.getElementById('agent-name-header');
    if (nameHeader) {
        nameHeader.value = agent.name;
        checkNameLimit(nameHeader); // Resize immediately
    }

    const descInput = document.getElementById('agent-desc');
    if (descInput) descInput.value = agent.description;

    const promptInput = document.getElementById('agent-prompt');
    if (promptInput) promptInput.value = agent.system_prompt;

    // Reset Chat
    chatHistory = [];
    const chatHistoryEl = document.getElementById('chat-history');
    if (chatHistoryEl) {
        chatHistoryEl.innerHTML = `
            <div class="empty-state">
                Start chatting with ${agent.name}...
            </div>
        `;
    }

    // Enable Chat Input
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    if (userInput) userInput.disabled = false;
    if (sendBtn) sendBtn.disabled = false;
}

function checkNameLimit(input) {
    // 1. Resize Input
    // Use a temporary span to measure text width? Or just approximate with ch
    // ch is approximate but usually fine for monospace or similar. 
    // For proportional fonts, it's harder.
    // Let's try a simple ch approximation first: length + 1
    // But since we have a max of 15, we can just set it to fit.

    const length = input.value.length;
    input.style.width = Math.max(10, length) + 'ch'; // Min 10ch so placeholder fits

    // 2. Show Warning
    const msg = document.getElementById('name-limit-msg');
    if (msg) {
        if (length >= 15) {
            msg.classList.add('show');
        } else {
            msg.classList.remove('show');
        }
    }
}

// Debounce Utility
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Autosave Wrapper (1 second delay)
const autoSaveAgentConfig = debounce(() => {
    saveAgentConfig(true); // true = silent mode (optional, see below)
}, 1000);

function saveAgentConfig(silent = false) {
    const nameHeader = document.getElementById('agent-name-header');
    const descInput = document.getElementById('agent-desc');
    const promptInput = document.getElementById('agent-prompt');

    if (!nameHeader || !descInput || !promptInput) return;

    const name = nameHeader.value;
    const desc = descInput.value;
    const prompt = promptInput.value;

    if (!name) {
        if (!silent) alert("Please give your agent a name.");
        return;
    }

    // If creating new agent
    if (!currentAgentId) {
        // Don't autosave new agents until they have a name and are explicitly saved first time?
        // Or just create it? Let's create it if name exists.
        const id = `agent_${Date.now()}`;
        agents[id] = {
            id: id,
            name: name,
            description: desc,
            system_prompt: prompt
        };
        currentAgentId = id;

        // Update URL without reloading
        window.history.pushState({}, '', `orchestrator.html?agent=${id}`);

        // Enable Chat
        const userInput = document.getElementById('user-input');
        const sendBtn = document.getElementById('send-btn');
        if (userInput) userInput.disabled = false;
        if (sendBtn) sendBtn.disabled = false;

        // Reset Chat UI for new agent
        const agent = agents[currentAgentId];
        const chatHistoryEl = document.getElementById('chat-history');
        if (chatHistoryEl) {
            chatHistoryEl.innerHTML = `
                <div class="empty-state">
                    Start chatting with ${agent.name}...
                </div>
            `;
        }
    } else {
        // Updating existing agent
        agents[currentAgentId].name = name;
        agents[currentAgentId].description = desc;
        agents[currentAgentId].system_prompt = prompt;
    }

    // Persist to LocalStorage
    localStorage.setItem('mcp_agents', JSON.stringify(agents));

    renderAgentList();

    // Show Toast (only if not silent, or maybe show a subtle one?)
    // For autosave, we usually want a subtle indicator. 
    // Let's use the toast but maybe change text? 
    // For now, I'll keep the toast but maybe we can make it less intrusive later.
    const toast = document.getElementById("toast");
    toast.innerText = "Configuration Saved";
    toast.className = "toast show";
    setTimeout(function () { toast.className = toast.className.replace("show", ""); }, 2000);
}

// Theme Management
function toggleTheme() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
}

function updateThemeIcon(theme) {
    const icon = document.getElementById('theme-icon');
    if (!icon) return;

    if (theme === 'dark') {
        // Sun Icon
        icon.innerHTML = '<path d="M6.76 4.84l-1.8-1.79-1.41 1.41 1.79 1.79 1.42-1.41zM4 10.5H1v2h3v-2zm9-9.95h-2V3.5h2V.55zm7.45 3.91l-1.41-1.41-1.79 1.79 1.41 1.41 1.79-1.79zm-3.21 13.7l1.79 1.79 1.41-1.41-1.79-1.79-1.41 1.41zM20 10.5v2h3v-2h-3zm-8-5c-3.31 0-6 2.69-6 6s2.69 6 6 6 6-2.69 6-6-2.69-6-6-6zm-1 16.95h2V19.5h-2v2.95zm-7.45-3.91l1.41 1.41 1.79-1.8-1.41-1.41-1.79 1.8z"></path>';
    } else {
        // Moon Icon
        icon.innerHTML = '<path d="M12 3c-4.97 0-9 4.03-9 9s4.03 9 9 9 9-4.03 9-9c0-.46-.04-.92-.1-1.36-.98 1.37-2.58 2.26-4.4 2.26-3.03 0-5.5-2.47-5.5-5.5 0-1.82.89-3.42 2.26-4.4-.44-.06-.9-.1-1.36-.1z"></path>';
    }
}

// Initialize Theme
const savedTheme = localStorage.getItem('theme') || 'light';
document.documentElement.setAttribute('data-theme', savedTheme);
document.addEventListener('DOMContentLoaded', () => {
    updateThemeIcon(savedTheme);
});

function resetChat() {
    if (!currentAgentId) return;

    // Clear history array
    chatHistory = [];

    // Reset UI
    const agent = agents[currentAgentId];
    document.getElementById('chat-history').innerHTML = `
        <div class="empty-state">
            Start chatting with ${agent.name}...
        </div>
    `;

    // Enable input if it was disabled
    document.getElementById('user-input').disabled = false;
    document.getElementById('send-btn').disabled = false;
    document.getElementById('user-input').focus();
}

function handleKeyPress(event) {
    if (event.key === 'Enter') sendMessage();
}

async function sendMessage() {
    const input = document.getElementById('user-input');
    const message = input.value.trim();
    const model = document.getElementById('model-select').value;

    if (!message || !currentAgentId) return;

    // Clear input
    input.value = '';

    // Add User Message
    addMessage('user', message);

    // Disable send
    const sendBtn = document.getElementById('send-btn');
    sendBtn.disabled = true;

    try {
        // Send to Backend
        // Note: We send the CURRENT config, so dynamic changes work immediately
        const response = await fetch('http://localhost:8000/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                agent_id: currentAgentId,
                system_prompt: agents[currentAgentId].system_prompt, // Send dynamic prompt
                model: model, // Send selected model
                message: message,
                history: chatHistory // This now includes the latest user message added by addMessage
            })
        });

        if (!response.ok) throw new Error('Network error');

        const data = await response.json();

        // Add Assistant Message (with reasoning if available)
        addMessage('assistant', data.response, data.reasoning);

    } catch (error) {
        console.error(error);
        addMessage('assistant', 'Error: Could not connect to backend.');
    } finally {
        sendBtn.disabled = false;
        input.focus();
    }
}

function addMessage(role, text, reasoning = null) {
    const chatHistoryEl = document.getElementById('chat-history');
    const emptyState = chatHistoryEl.querySelector('.empty-state');
    if (emptyState) emptyState.remove();

    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;

    if (role === 'user') {
        // Simple Bubble for User
        msgDiv.innerText = text;

        // Optional: Add timestamp for user too? 
        // For now, keep it simple as per image (user bubble is simple)
        // But image shows timestamp for user too "You 04:48 PM"
        // Let's stick to simple bubble first, maybe add timestamp later if requested.
        // Actually, let's add a small timestamp inside or above.
        // The image shows "You 04:48 PM" above the bubble.
        // For now, I'll put text inside.

    } else {
        // Complex Layout for Assistant
        const agentName = agents[currentAgentId]?.name || "Agent";
        const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        const hasReasoning = reasoning && reasoning.length > 0;

        msgDiv.innerHTML = `
            <div class="assistant-avatar">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                    <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"></path>
                </svg>
            </div>
            <div class="assistant-body">
                <div class="assistant-header">
                    <span class="agent-name-display">${agentName}</span>
                    <span class="msg-timestamp">${time}</span>
                    ${hasReasoning ? `
                        <button class="reasoning-toggle" onclick="toggleReasoning(this)">
                            Show Reasoning
                            <svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor">
                                <path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"></path>
                            </svg>
                        </button>
                    ` : ''}
                </div>
                <div class="message-text">${text}</div>
                ${hasReasoning ? `<div class="reasoning-content">${reasoning}</div>` : ''}
            </div>
        `;
    }

    chatHistoryEl.appendChild(msgDiv);
    chatHistoryEl.scrollTop = chatHistoryEl.scrollHeight;

    // Add to history
    chatHistory.push({ role, content: text, reasoning });
}

function toggleReasoning(btn) {
    const content = btn.parentElement.parentElement.querySelector('.reasoning-content');
    const isHidden = content.style.display === 'none' || content.style.display === '';

    if (isHidden) {
        content.style.display = 'block';
        btn.innerHTML = `Hide Reasoning <svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor" style="transform: rotate(180deg);"><path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"></path></svg>`;
    } else {
        content.style.display = 'none';
        btn.innerHTML = `Show Reasoning <svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor"><path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"></path></svg>`;
    }
}
