let currentAgent = null;
let chatHistory = [];

const AGENTS = {
    'agent_1': { name: 'Nova', color: '#0ea5e9' },
    'agent_2': { name: 'Blaze', color: '#ec4899' }
};

function openChat(agentId) {
    currentAgent = agentId;
    chatHistory = []; // Reset history for new session

    // Update UI
    const agent = AGENTS[agentId];
    document.getElementById('chat-agent-name').innerText = agent.name;

    const avatar = document.getElementById('chat-avatar');
    avatar.style.background = agentId === 'agent_1'
        ? 'linear-gradient(135deg, #0ea5e9, #2563eb)'
        : 'linear-gradient(135deg, #ec4899, #db2777)';

    // Clear previous messages except system message
    const historyDiv = document.getElementById('chat-history');
    historyDiv.innerHTML = `
        <div class="message system-message">
            Connection established with ${agent.name}. How can I assist you today?
        </div>
    `;

    // Show modal
    document.getElementById('chat-modal').classList.remove('hidden');
    document.getElementById('user-input').focus();
}

function closeChat() {
    document.getElementById('chat-modal').classList.add('hidden');
    currentAgent = null;
}

function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

async function sendMessage() {
    const input = document.getElementById('user-input');
    const message = input.value.trim();

    if (!message || !currentAgent) return;

    // Clear input
    input.value = '';

    // Add User Message to UI
    appendMessage('user', message);

    // Disable send button while waiting
    const sendBtn = document.getElementById('send-btn');
    sendBtn.disabled = true;

    try {
        // Call Backend
        const response = await fetch('http://localhost:8000/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                agent_id: currentAgent,
                message: message,
                history: chatHistory
            })
        });

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        const data = await response.json();

        // Add Assistant Message to UI
        appendMessage('assistant', data.response);

        // Update History
        chatHistory.push({ role: 'user', content: message });
        chatHistory.push({ role: 'assistant', content: data.response });

    } catch (error) {
        console.error('Error:', error);
        appendMessage('system-message', 'Error: Could not connect to the agent. Please check if the backend is running.');
    } finally {
        sendBtn.disabled = false;
        input.focus();
    }
}

function appendMessage(role, text) {
    const historyDiv = document.getElementById('chat-history');
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role}`;

    // Convert newlines to <br> for display
    msgDiv.innerHTML = text.replace(/\n/g, '<br>');

    historyDiv.appendChild(msgDiv);
    historyDiv.scrollTop = historyDiv.scrollHeight;
}
