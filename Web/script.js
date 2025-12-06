let agents = {
    "agent_1": {
        id: "agent_1",
        name: "Nova",
        description: "Futuristic AI assistant with AWS capabilities.",
        system_prompt: "You are Nova, a futuristic AI assistant. You have access to AWS tools. Use them when requested. Be precise."
    },
    "agent_2": {
        id: "agent_2",
        name: "Blaze",
        description: "Creative AI with a flair for the dramatic.",
        system_prompt: "You are Blaze, a creative AI. You can also manage AWS resources if asked, but you do it with style."
    }
};

let currentAgentId = null;
let chatHistory = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    renderAgentList();
});

function renderAgentList() {
    const list = document.getElementById('agent-list');
    list.innerHTML = '';

    Object.values(agents).forEach(agent => {
        const item = document.createElement('div');
        item.className = `agent-item ${currentAgentId === agent.id ? 'active' : ''}`;
        item.onclick = () => selectAgent(agent.id);
        item.innerHTML = `<span>🤖</span> ${agent.name}`;
        list.appendChild(item);
    });
}

function selectAgent(id) {
    currentAgentId = id;
    const agent = agents[id];

    // Update UI Active State
    renderAgentList();

    // Populate Config Panel
    document.getElementById('agent-name').value = agent.name;
    document.getElementById('agent-desc').value = agent.description;
    document.getElementById('agent-prompt').value = agent.system_prompt;

    // Reset Chat
    chatHistory = [];
    document.getElementById('chat-header-name').innerText = agent.name;
    document.getElementById('chat-history').innerHTML = `
        <div class="message assistant">
            Hello! I am ${agent.name}. How can I help you?
        </div>
    `;

    // Enable Chat Input
    document.getElementById('user-input').disabled = false;
    document.getElementById('send-btn').disabled = false;
}

function createNewAgent() {
    const id = `agent_${Date.now()}`;
    agents[id] = {
        id: id,
        name: "New Agent",
        description: "A new custom agent",
        system_prompt: "You are a helpful AI assistant."
    };
    selectAgent(id);
}

function saveAgentConfig() {
    if (!currentAgentId) return;

    const name = document.getElementById('agent-name').value;
    const desc = document.getElementById('agent-desc').value;
    const prompt = document.getElementById('agent-prompt').value;

    agents[currentAgentId].name = name;
    agents[currentAgentId].description = desc;
    agents[currentAgentId].system_prompt = prompt;

    renderAgentList();
    document.getElementById('chat-header-name').innerText = name;

    // In a real app, we would send this to the backend to persist
    alert('Agent configuration saved!');
}

function resetChat() {
    if (!currentAgentId) return;

    // Clear history array
    chatHistory = [];

    // Reset UI
    const agent = agents[currentAgentId];
    document.getElementById('chat-history').innerHTML = `
        <div class="message assistant">
            Hello! I am ${agent.name}. How can I help you?
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
    appendMessage('user', message);

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
                history: chatHistory
            })
        });

        if (!response.ok) throw new Error('Network error');

        const data = await response.json();

        // Add Assistant Message
        appendMessage('assistant', data.response);

        // Update History
        chatHistory.push({ role: 'user', content: message });
        chatHistory.push({ role: 'assistant', content: data.response });

    } catch (error) {
        console.error(error);
        appendMessage('assistant', 'Error: Could not connect to backend.');
    } finally {
        sendBtn.disabled = false;
        input.focus();
    }
}

function appendMessage(role, text) {
    const historyDiv = document.getElementById('chat-history');
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;
    msgDiv.innerHTML = text.replace(/\n/g, '<br>');
    historyDiv.appendChild(msgDiv);
    historyDiv.scrollTop = historyDiv.scrollHeight;
}
