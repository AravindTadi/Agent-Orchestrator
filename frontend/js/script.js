// API Base URL
const API_BASE = 'http://localhost:8000';

// Agents storage (populated from API)
let agents = {};
let currentAgentId = null;
let chatHistory = [];

function toggleSidebar() {
    document.getElementById('main-nav').classList.toggle('open');
    document.getElementById('sidebar-overlay').classList.toggle('show');
}

// Initialize - Load agents from API (only for pages that need the agent list)
document.addEventListener('DOMContentLoaded', async () => {
    // Skip this initialization for analytics page - it has its own init
    if (window.location.pathname.includes('analytics.html')) {
        console.log('Skipping script.js initialization for analytics page');
        return;
    }

    await loadAgentsFromAPI();

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

// Load agents from backend API
async function loadAgentsFromAPI() {
    try {
        const response = await fetch(`${API_BASE}/agents`);
        if (!response.ok) throw new Error('Failed to load agents');

        const data = await response.json();
        agents = {};
        data.agents.forEach(agent => {
            agents[agent.id] = agent;
        });

        renderAgentList();
        console.log(`Loaded ${data.count} agents from API`);
    } catch (error) {
        console.error('Error loading agents from API:', error);
        // Fallback to localStorage if API fails
        agents = JSON.parse(localStorage.getItem('mcp_agents')) || {
            "agent_default": {
                id: "agent_default",
                name: "My First Agent",
                description: "A helpful AI assistant ready to be configured.",
                system_prompt: "You are a helpful AI assistant."
            }
        };
        renderAgentList();
    }
}

function initCreateMode() {
    currentAgentId = null; // No ID yet

    // Clear Config Panel
    const nameHeader = document.getElementById('agent-name-header');
    const descInput = document.getElementById('agent-desc');
    const promptInput = document.getElementById('agent-prompt');
    const deleteBtn = document.getElementById('delete-agent-btn');
    const saveBtn = document.getElementById('save-agent-btn');
    const formActions = document.getElementById('form-actions');

    if (nameHeader) nameHeader.value = "";
    if (descInput) descInput.value = "";
    if (promptInput) promptInput.value = "";
    if (deleteBtn) deleteBtn.style.display = 'none'; // Hide delete for new agents
    if (formActions) formActions.style.display = 'block'; // Show save button area
    if (saveBtn) saveBtn.textContent = 'Create Agent'; // Change button text

    // Reset Chat to Empty
    const chatHistory = document.getElementById('chat-history');
    if (chatHistory) {
        chatHistory.innerHTML = `
            <div class="empty-state">
                Configure your new agent and click "Create Agent" to save it.
            </div>
        `;
    }

    // Disable Chat Input until saved
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    if (userInput) userInput.disabled = true;
    if (sendBtn) sendBtn.disabled = true;

    // Clear document list
    const docList = document.getElementById('document-list');
    if (docList) docList.innerHTML = '<p class="hint" style="text-align:center;">Save the agent first to add documents.</p>';

    renderAgentList();
}

function renderAgentList() {
    const list = document.getElementById('agent-list');

    // Skip if this page doesn't have an agent list (e.g. analytics.html)
    if (!list) return;

    list.innerHTML = '';

    // Add "Back to Dashboard" link
    const backLink = document.createElement('div');
    backLink.className = 'back-link';
    backLink.innerHTML = '<span>&larr;</span> Back to Dashboard';
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
    if (descInput) descInput.value = agent.description || '';

    const promptInput = document.getElementById('agent-prompt');
    if (promptInput) promptInput.value = agent.system_prompt || '';

    // Show delete button (but disable for default agent)
    const deleteBtn = document.getElementById('delete-agent-btn');
    if (deleteBtn) {
        deleteBtn.style.display = 'flex';
        deleteBtn.disabled = (id === 'agent_default');
    }

    // Hide save button for existing agents (autosave handles updates)
    const formActions = document.getElementById('form-actions');
    if (formActions) formActions.style.display = 'none';

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

    // Load Knowledge Base documents
    loadDocuments();
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

async function saveAgentConfig(silent = false) {
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

    try {
        // If creating new agent
        if (!currentAgentId) {
            const response = await fetch(`${API_BASE}/agents`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: name,
                    description: desc,
                    system_prompt: prompt
                })
            });

            if (!response.ok) throw new Error('Failed to create agent');

            const data = await response.json();
            const newAgent = data.agent;
            currentAgentId = newAgent.id;
            agents[currentAgentId] = newAgent;

            // Update URL without reloading
            window.history.pushState({}, '', `orchestrator.html?agent=${currentAgentId}`);

            // Enable Chat
            const userInput = document.getElementById('user-input');
            const sendBtn = document.getElementById('send-btn');
            if (userInput) userInput.disabled = false;
            if (sendBtn) sendBtn.disabled = false;

            // Reset Chat UI for new agent
            const chatHistoryEl = document.getElementById('chat-history');
            if (chatHistoryEl) {
                chatHistoryEl.innerHTML = `
                    <div class="empty-state">
                        Start chatting with ${newAgent.name}...
                    </div>
                `;
            }

            // Show delete button after creating
            const deleteBtn = document.getElementById('delete-agent-btn');
            if (deleteBtn) {
                deleteBtn.style.display = 'flex';
                deleteBtn.disabled = false;
            }

            // Hide the save button (agent is now created)
            const formActions = document.getElementById('form-actions');
            if (formActions) formActions.style.display = 'none';

            // Reload documents for this new agent
            loadDocuments();
        } else {
            // Updating existing agent
            const response = await fetch(`${API_BASE}/agents/${currentAgentId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: name,
                    description: desc,
                    system_prompt: prompt
                })
            });

            if (!response.ok) throw new Error('Failed to update agent');

            const data = await response.json();
            agents[currentAgentId] = data.agent;
        }

        // Also save to localStorage as backup
        localStorage.setItem('mcp_agents', JSON.stringify(agents));

        renderAgentList();

        // Show Toast
        const toast = document.getElementById("toast");
        toast.innerText = "Configuration Saved";
        toast.className = "toast show";
        setTimeout(function () { toast.className = toast.className.replace("show", ""); }, 2000);

    } catch (error) {
        console.error('Save error:', error);
        if (!silent) {
            showToast('Failed to save: ' + error.message);
        }
    }
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

// Initialize Theme (global across all pages)
const savedTheme = localStorage.getItem('theme') || 'light';
document.documentElement.setAttribute('data-theme', savedTheme);

document.addEventListener('DOMContentLoaded', () => {
    const themeCheckbox = document.getElementById('theme-checkbox');
    if (themeCheckbox) {
        themeCheckbox.checked = savedTheme === 'dark';
        themeCheckbox.addEventListener('change', () => {
            const newTheme = themeCheckbox.checked ? 'dark' : 'light';
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
        });
    }
});

function resetChat() {
    if (!currentAgentId) return;

    // Clear history array
    chatHistory = [];

    // Reset session for analytics (will create new session on next message)
    if (typeof currentSessionId !== 'undefined') {
        currentSessionId = null;
    }

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

// Current chat session ID for analytics tracking
let currentSessionId = null;

// Create a new chat session
async function createChatSession(agentId) {
    try {
        const response = await fetch('http://localhost:8000/chat/sessions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                agent_id: agentId,
                title: 'New Chat'
            })
        });
        if (response.ok) {
            const data = await response.json();
            return data.session?.id || null;
        }
    } catch (error) {
        console.error('Failed to create chat session:', error);
    }
    return null;
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
        // Create session if doesn't exist (for analytics tracking)
        if (!currentSessionId) {
            currentSessionId = await createChatSession(currentAgentId);
        }

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
                history: chatHistory, // This now includes the latest user message added by addMessage
                session_id: currentSessionId // Track for analytics
            })
        });

        if (!response.ok) throw new Error('Network error');

        const data = await response.json();

        // Add Assistant Message (with reasoning and sources if available)
        addMessage('assistant', data.response, data.reasoning, data.sources);

    } catch (error) {
        console.error(error);
        addMessage('assistant', 'Error: Could not connect to backend.');
    } finally {
        sendBtn.disabled = false;
        input.focus();
    }
}

function addMessage(role, text, reasoning = null, sources = null) {
    const chatHistoryEl = document.getElementById('chat-history');
    const emptyState = chatHistoryEl.querySelector('.empty-state');
    if (emptyState) emptyState.remove();

    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;

    if (role === 'user') {
        // Simple Bubble for User
        msgDiv.innerText = text;

    } else {
        // Complex Layout for Assistant
        const agentName = agents[currentAgentId]?.name || "Agent";
        const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

        const hasReasoning = reasoning && reasoning.length > 0;
        const hasSources = sources && sources.length > 0;

        // Build sources HTML
        let sourcesHtml = '';
        if (hasSources) {
            const pills = sources.map(s => {
                const name = s.metadata?.filename || s.metadata?.title || s.document_id;
                return `<span class="source-pill" title="Score: ${s.score}">${name}</span>`;
            }).join('');
            sourcesHtml = `
                <div class="sources-section">
                    <span class="sources-label">Sources:</span>
                    ${pills}
                </div>
            `;
        }

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
                ${sourcesHtml}
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

// ==========================================
// DOCUMENT MANAGEMENT (RAG)
// ==========================================

async function loadDocuments() {
    if (!currentAgentId) return;

    try {
        const response = await fetch(`http://localhost:8000/documents/${currentAgentId}`);
        const data = await response.json();

        renderDocumentList(data.documents || []);
        updateDocCount(data.count || 0);
    } catch (error) {
        console.error('Error loading documents:', error);
    }
}

function renderDocumentList(documents) {
    const list = document.getElementById('document-list');
    if (!list) return;

    if (documents.length === 0) {
        list.innerHTML = '<p class="hint" style="text-align:center;">No documents yet. Upload files or add URLs.</p>';
        return;
    }

    list.innerHTML = documents.map(doc => {
        const meta = doc.metadata || {};
        const icon = getIconForType(meta.type);
        const name = meta.filename || meta.title || meta.url || doc.document_id;
        const info = meta.chunks ? `${meta.chunks} chunks` : '';

        return `
            <div class="document-item" data-id="${doc.document_id}">
                <div class="document-info">
                    <span class="document-icon">${icon}</span>
                    <span class="document-name" title="${name}">${name}</span>
                    <span class="document-meta">${info}</span>
                </div>
                <button class="delete-doc-btn" onclick="deleteDocument('${doc.document_id}', event)" title="Delete" type="button">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                        <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"></path>
                    </svg>
                </button>
            </div>
        `;
    }).join('');
}

function getIconForType(type) {
    // Return simple text labels or code for now, or SVGs if we had a map
    // For now, let's return a generic file SVG string
    const svgMap = {
        'txt': '<svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/></svg>',
        'pdf': '<svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M20 2H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-8.5 7.5c0 .83-.67 1.5-1.5 1.5H9v2H7.5V7H10c.83 0 1.5.67 1.5 1.5v2.5zm2.5 3.5h-2.5V7h2.5c.83 0 1.5.67 1.5 1.5v2.5c0 .83-.67 1.5-1.5 1.5zm4.5 0h-1.5v-1h1.5V9h-1.5v-1h2V7h-3.5v6H18v-2z"/></svg>',
        'web': '<svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/></svg>'
    };
    return svgMap[type] || svgMap['txt'];
}

function updateDocCount(count) {
    const el = document.getElementById('doc-count');
    if (el) {
        el.textContent = `${count} document${count !== 1 ? 's' : ''}`;
    }
}

// Drag & Drop Handlers
function handleDragOver(event) {
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.classList.add('dragover');
}

function handleDragLeave(event) {
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.classList.remove('dragover');
}

function handleDrop(event) {
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.classList.remove('dragover');

    const files = event.dataTransfer.files;
    if (files.length > 0) {
        uploadFiles(files);
    }
}

function handleFileSelect(event) {
    const files = event.target.files;
    if (files.length > 0) {
        uploadFiles(files);
    }
    // Reset input so same file can be selected again
    event.target.value = '';
}

async function uploadFiles(files) {
    if (!currentAgentId) {
        alert('Please select or create an agent first.');
        return;
    }

    const documentList = document.getElementById('document-list');

    for (const file of files) {
        // Show upload progress
        const progressId = `upload_${Date.now()}`;
        const progressEl = document.createElement('div');
        progressEl.className = 'upload-progress';
        progressEl.id = progressId;
        progressEl.innerHTML = `<div class="spinner"></div><span>Uploading ${file.name}...</span>`;
        documentList.insertBefore(progressEl, documentList.firstChild);

        try {
            const formData = new FormData();
            formData.append('agent_id', currentAgentId);
            formData.append('file', file);

            const response = await fetch('http://localhost:8000/documents/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Upload failed');
            }

            const data = await response.json();
            console.log('Upload success:', data);

            // Remove progress and refresh list
            document.getElementById(progressId)?.remove();
            loadDocuments();

            // Show toast
            showToast(`Uploaded: ${file.name}`);

        } catch (error) {
            console.error('Upload error:', error);
            const progress = document.getElementById(progressId);
            if (progress) {
                progress.innerHTML = `<span style="color:#da1e28;">Failed: ${file.name}</span>`;
                setTimeout(() => progress.remove(), 3000);
            }
        }
    }
}

async function addUrl() {
    const input = document.getElementById('url-input');
    const url = input.value.trim();

    if (!url) return;
    if (!currentAgentId) {
        alert('Please select or create an agent first.');
        return;
    }

    // Validate URL
    try {
        new URL(url);
    } catch {
        alert('Please enter a valid URL.');
        return;
    }

    const documentList = document.getElementById('document-list');

    // Show progress
    const progressId = `upload_${Date.now()}`;
    const progressEl = document.createElement('div');
    progressEl.className = 'upload-progress';
    progressEl.id = progressId;
    progressEl.innerHTML = `<div class="spinner"></div><span>Fetching ${url}...</span>`;
    documentList.insertBefore(progressEl, documentList.firstChild);

    input.value = '';

    try {
        const response = await fetch('http://localhost:8000/documents/url', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                agent_id: currentAgentId,
                url: url
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to add URL');
        }

        const data = await response.json();
        console.log('URL added:', data);

        document.getElementById(progressId)?.remove();
        loadDocuments();

        showToast(`Added: ${url}`);

    } catch (error) {
        console.error('URL add error:', error);
        const progress = document.getElementById(progressId);
        if (progress) {
            progress.innerHTML = `<span style="color:#da1e28;">Failed: ${error.message}</span>`;
            setTimeout(() => progress.remove(), 3000);
        }
    }
}

async function deleteDocument(documentId, event) {
    // Prevent event bubbling
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }

    if (!currentAgentId) return;

    // No confirmation needed for documents - they can be re-uploaded
    try {
        const response = await fetch(`${API_BASE}/documents/${currentAgentId}/${documentId}`, {
            method: 'DELETE'
        });

        if (!response.ok) throw new Error('Delete failed');

        loadDocuments();
        showToast('Document deleted');

    } catch (error) {
        console.error('Delete error:', error);
        showToast('Failed to delete document');
    }
}

function showToast(message) {
    const toast = document.getElementById("toast");
    if (!toast) return;
    toast.innerText = message;
    toast.className = "toast show";
    setTimeout(() => { toast.className = toast.className.replace("show", ""); }, 3000);
}

// Delete current agent - show modal
function deleteCurrentAgent(event) {
    // Prevent event bubbling
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }

    if (!currentAgentId) {
        showToast('No agent selected');
        return;
    }

    if (currentAgentId === 'agent_default') {
        showToast('Cannot delete the default agent');
        return;
    }

    // Show custom modal
    const agent = agents[currentAgentId];
    const modal = document.getElementById('delete-modal');
    const message = document.getElementById('delete-modal-message');

    if (modal && message) {
        message.textContent = `Are you sure you want to delete "${agent?.name || currentAgentId}"?`;
        modal.style.display = 'flex';
    }
}

// Close delete modal
function closeDeleteModal() {
    const modal = document.getElementById('delete-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Confirm delete from modal
async function confirmDeleteAgent() {
    closeDeleteModal();

    if (!currentAgentId) return;

    try {
        const response = await fetch(`${API_BASE}/agents/${currentAgentId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to delete agent');
        }

        // Remove from local state
        delete agents[currentAgentId];
        localStorage.setItem('mcp_agents', JSON.stringify(agents));

        showToast('Agent deleted');

        // Redirect to first available agent or dashboard
        const remainingIds = Object.keys(agents);
        if (remainingIds.length > 0) {
            selectAgent(remainingIds[0]);
        } else {
            window.location.href = 'index.html';
        }

    } catch (error) {
        console.error('Delete agent error:', error);
        showToast(`${error.message}`);
    }
}

// Create new agent - show template picker
function createNewAgent() {
    openTemplateModal();
}

// Template Modal Functions
async function openTemplateModal() {
    const modal = document.getElementById('template-modal');
    if (modal) {
        modal.classList.add('show');
        await loadTemplates();
    }
}

function closeTemplateModal(event) {
    if (!event || event.target.id === 'template-modal') {
        const modal = document.getElementById('template-modal');
        if (modal) modal.classList.remove('show');
    }
}

async function loadTemplates() {
    try {
        const response = await fetch(`${API_BASE}/templates`);
        if (response.ok) {
            const data = await response.json();
            renderTemplates(data.templates);
        }
    } catch (error) {
        console.error('Failed to load templates:', error);
    }
}

function renderTemplates(templates) {
    const grid = document.getElementById('template-grid');
    if (!grid) return;

    // Keep only the first "Blank Agent" card
    const blankCard = grid.querySelector('.template-card');
    grid.innerHTML = '';
    if (blankCard) grid.appendChild(blankCard);

    templates.forEach(template => {
        const card = document.createElement('div');
        card.className = 'template-card';
        card.onclick = () => createFromTemplate(template.id);
        card.innerHTML = `
            <div class="template-icon">${template.icon || ''}</div>
            <div class="template-info">
                <h4>${template.name}</h4>
                <p>${template.description}</p>
            </div>
            <span class="template-category">${template.category}</span>
        `;
        grid.appendChild(card);
    });
}

function createBlankAgent() {
    closeTemplateModal();
    window.location.href = 'orchestrator.html?mode=create';
}

async function createFromTemplate(templateId) {
    try {
        const response = await fetch(`${API_BASE}/agents/from-template/${templateId}`, {
            method: 'POST'
        });

        if (response.ok) {
            const data = await response.json();
            closeTemplateModal();
            showToast(`Created agent: ${data.agent.name}`);
            window.location.href = `orchestrator.html?agent=${data.agent.id}`;
        } else {
            showToast('Failed to create agent');
        }
    } catch (error) {
        console.error('Error creating from template:', error);
        showToast('Failed to create agent');
    }
}

// Profile button - redirect to login/profile page
function openProfile() {
    window.location.href = 'login.html';
}

// --- Settings & Integrations ---

function openSettings() {
    const modal = document.getElementById('settings-modal');
    if (modal) {
        modal.style.display = 'flex';
        loadSettings();
    }
}

function closeSettings() {
    const modal = document.getElementById('settings-modal');
    if (modal) modal.style.display = 'none';
}

function switchSettingsTab(tab) {
    const tabs = document.querySelectorAll('.settings-tab');
    const contents = document.querySelectorAll('.settings-content');

    tabs.forEach(t => t.classList.remove('active'));
    contents.forEach(c => c.style.display = 'none');

    if (tab === 'aws') {
        tabs[0].classList.add('active');
        document.getElementById('aws-settings').style.display = 'block';
    } else {
        tabs[1].classList.add('active');
        document.getElementById('datadog-settings').style.display = 'block';
    }
}

async function loadSettings() {
    try {
        const token = localStorage.getItem('auth_token');
        if (!token) return;

        const response = await fetch(`${API_BASE}/settings`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.ok) {
            const data = await response.json();
            const s = data.settings;

            if (s.aws_access_key) document.getElementById('aws-access-key').value = s.aws_access_key;
            if (s.aws_secret_key) document.getElementById('aws-secret-key').value = s.aws_secret_key; // Will be masked
            if (s.aws_region) document.getElementById('aws-region').value = s.aws_region;
            if (s.aws_log_group) document.getElementById('aws-log-group').value = s.aws_log_group;

            if (s.dd_api_key) document.getElementById('dd-api-key').value = s.dd_api_key; // Will be masked
            if (s.dd_site) document.getElementById('dd-site').value = s.dd_site;
        }
    } catch (error) {
        console.error('Failed to load settings:', error);
    }
}

async function saveAwsSettings() {
    const accessKey = document.getElementById('aws-access-key').value;
    const secretKey = document.getElementById('aws-secret-key').value;
    const region = document.getElementById('aws-region').value;
    const logGroup = document.getElementById('aws-log-group').value;

    if (!accessKey || !secretKey || !region) {
        showToast('Please fill in all AWS fields');
        return;
    }

    try {
        const token = localStorage.getItem('auth_token');
        const response = await fetch(`${API_BASE}/settings/aws`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                access_key: accessKey,
                secret_key: secretKey,
                region: region,
                log_group: logGroup
            })
        });

        if (response.ok) {
            showToast('AWS Settings Saved');
            closeSettings();
        } else {
            throw new Error('Failed to save');
        }
    } catch (error) {
        showToast('Error saving settings');
    }
}

async function saveDatadogSettings() {
    const apiKey = document.getElementById('dd-api-key').value;
    const site = document.getElementById('dd-site').value;

    if (!apiKey) {
        showToast('Please enter Datadog API Key');
        return;
    }

    try {
        const token = localStorage.getItem('auth_token');
        const response = await fetch(`${API_BASE}/settings/datadog`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                api_key: apiKey,
                site: site
            })
        });

        if (response.ok) {
            showToast('Datadog Settings Saved');
            closeSettings();
        } else {
            throw new Error('Failed to save');
        }
    } catch (error) {
        showToast('Error saving settings');
    }
}

// ==================== Profile Dropdown ====================

// Toggle profile menu
function toggleProfileMenu() {
    const menu = document.getElementById('profile-menu');
    menu.classList.toggle('show');

    // Load user info
    loadUserInfo();
}

// Close profile menu when clicking outside
document.addEventListener('click', (e) => {
    const dropdown = document.getElementById('profile-dropdown');
    const menu = document.getElementById('profile-menu');
    if (dropdown && menu && !dropdown.contains(e.target)) {
        menu.classList.remove('show');
    }
});

// Load user info from auth
async function loadUserInfo() {
    const token = localStorage.getItem('auth_token');
    if (!token) {
        document.getElementById('profile-name').textContent = 'Guest User';
        document.getElementById('profile-email').textContent = 'Not logged in';
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/auth/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (response.ok) {
            const data = await response.json();
            document.getElementById('profile-name').textContent = data.email.split('@')[0];
            document.getElementById('profile-email').textContent = data.email;
        }
    } catch (error) {
        console.error('Failed to load user info:', error);
    }
}

// Open Settings page (Integrations)
function openSettingsPage() {
    window.location.href = 'integrations.html';
}

// Open Region Selector Modal
function openRegionSelector() {
    document.getElementById('profile-menu').classList.remove('show');
    document.getElementById('region-modal').classList.add('show');

    // Load saved region
    const savedRegion = localStorage.getItem('selected_region') || 'us-east-1';
    updateRegionSelection(savedRegion);
}

function closeRegionModal(event) {
    if (!event || event.target.id === 'region-modal') {
        document.getElementById('region-modal').classList.remove('show');
    }
}

function selectRegion(regionCode, regionName) {
    localStorage.setItem('selected_region', regionCode);
    localStorage.setItem('selected_region_name', regionName);

    // Update badge
    const badge = document.getElementById('current-region');
    if (badge) {
        badge.textContent = regionCode.split('-').slice(0, 2).map(s => s.charAt(0).toUpperCase() + s.slice(1)).join('-');
    }

    updateRegionSelection(regionCode);
    showToast(`Region set to ${regionName}`);

    setTimeout(() => closeRegionModal(), 500);
}

function updateRegionSelection(selectedCode) {
    const options = document.querySelectorAll('.region-option');
    options.forEach(opt => {
        const code = opt.querySelector('.region-code').textContent;
        if (code === selectedCode) {
            opt.classList.add('active');
        } else {
            opt.classList.remove('active');
        }
    });
}

// Open API Keys Modal
function openApiKeys() {
    document.getElementById('profile-menu').classList.remove('show');
    document.getElementById('apikeys-modal').classList.add('show');
    loadApiKey();
}

function closeApiKeysModal(event) {
    if (!event || event.target.id === 'apikeys-modal') {
        document.getElementById('apikeys-modal').classList.remove('show');
    }
}

function loadApiKey() {
    let apiKey = localStorage.getItem('agenthub_api_key');
    if (!apiKey) {
        apiKey = generateApiKeyString();
        localStorage.setItem('agenthub_api_key', apiKey);
    }
    document.getElementById('api-key-display').value = apiKey;
}

function generateApiKeyString() {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    let key = 'ah_';
    for (let i = 0; i < 32; i++) {
        key += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return key;
}

function copyApiKey() {
    const input = document.getElementById('api-key-display');
    input.select();
    document.execCommand('copy');
    showToast('API Key copied to clipboard');
}

function regenerateApiKey() {
    if (confirm('Are you sure? The old key will stop working.')) {
        const newKey = generateApiKeyString();
        localStorage.setItem('agenthub_api_key', newKey);
        document.getElementById('api-key-display').value = newKey;
        showToast('API Key regenerated');
    }
}

function generateNewApiKey() {
    regenerateApiKey();
}

// Handle Logout
async function handleLogout() {
    const token = localStorage.getItem('auth_token');

    try {
        if (token) {
            await fetch(`${API_BASE}/auth/logout`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });
        }
    } catch (error) {
        console.error('Logout error:', error);
    }

    // Clear local storage
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_email');

    showToast('Logged out successfully');

    setTimeout(() => {
        window.location.href = 'login.html';
    }, 1000);
}

// Load region badge on page load
document.addEventListener('DOMContentLoaded', () => {
    const savedRegion = localStorage.getItem('selected_region') || 'us-east-1';
    const badge = document.getElementById('current-region');
    if (badge) {
        badge.textContent = savedRegion.split('-').slice(0, 2).map(s => s.charAt(0).toUpperCase() + s.slice(1)).join('-');
    }
});

