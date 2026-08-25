let ws = null;
let wsConnected = false;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;

function connectWebSocket(userId, token) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        console.log('WebSocket already connected');
        return;
    }

    try {
        const wsUrl = `ws://localhost:8000/ws/${userId}?token=${token}`;
        ws = new WebSocket(wsUrl);

        ws.onopen = function() {
            console.log('✅ WebSocket connected');
            wsConnected = true;
            reconnectAttempts = 0;
            updateConnectionStatus('Connected ✅', '#48bb78');
        };

        ws.onmessage = function(event) {
            try {
                const data = JSON.parse(event.data);
                console.log('📨 Received:', data);
                handleWebSocketMessage(data);
            } catch (e) {
                console.log('📨 Received (text):', event.data);
                if (event.data === 'pong') {}
            }
        };

        ws.onclose = function(event) {
            console.log('❌ WebSocket disconnected:', event.code, event.reason);
            wsConnected = false;
            updateConnectionStatus('Disconnected ❌', '#e53e3e');
            if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                reconnectAttempts++;
                setTimeout(() => {
                    console.log(`🔄 Reconnecting (attempt ${reconnectAttempts})...`);
                    connectWebSocket(userId, token);
                }, 3000);
            }
        };

        ws.onerror = function(error) {
            console.error('⚠️ WebSocket error:', error);
            updateConnectionStatus('Error ⚠️', '#ed8936');
        };

    } catch (error) {
        console.error('Failed to create WebSocket:', error);
    }
}

function handleWebSocketMessage(data) {
    if (data.type === 'connection') {
        showNotification(data.message, 'success');
    } else if (data.type === 'ticket_update') {
        const action = data.action;
        const ticket = data.ticket;
        let message = '';
        if (action === 'created') {
            message = `🎫 New ticket: "${ticket.title}" created by ${ticket.submitter_name}`;
        } else if (action === 'updated') {
            message = `📝 Ticket #${ticket.id} updated: "${ticket.title}"`;
        }
        showNotification(message, 'info');
        if (typeof loadTickets === 'function') {
            loadTickets();
        }
    } else if (data.type === 'echo') {
        console.log('Echo:', data.message);
    }
}

function showNotification(message, type = 'info') {
    let container = document.getElementById('notification-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notification-container';
        container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 9999;
            max-width: 400px;
            width: 100%;
        `;
        document.body.appendChild(container);
    }

    const colors = {
        'info': { bg: '#1a365d', border: '#4299e1', text: '#bee3f8' },
        'success': { bg: '#1a3a2a', border: '#48bb78', text: '#c6f6d5' },
        'error': { bg: '#3a1a1a', border: '#fc8181', text: '#fed7d7' },
        'warning': { bg: '#3a2a1a', border: '#ed8936', text: '#fbd38d' }
    };
    const color = colors[type] || colors.info;

    const notification = document.createElement('div');
    notification.style.cssText = `
        background: ${color.bg};
        border-left: 4px solid ${color.border};
        color: ${color.text};
        padding: 12px 16px;
        margin-bottom: 10px;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.4);
        font-size: 14px;
        animation: slideIn 0.3s ease;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    `;
    notification.textContent = message;
    container.appendChild(notification);

    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transition = 'opacity 0.5s ease';
        setTimeout(() => {
            notification.remove();
        }, 500);
    }, 5000);
}

function updateConnectionStatus(text, color) {
    let status = document.getElementById('ws-status');
    if (!status) {
        status = document.createElement('div');
        status.id = 'ws-status';
        status.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            z-index: 9999;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        `;
        document.body.appendChild(status);
    }
    status.textContent = `🔌 ${text}`;
    status.style.background = color;
    status.style.color = 'white';
}

function startHeartbeat() {
    setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
        }
    }, 30000);
}

const styleSheet = document.createElement("style");
styleSheet.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
`;
document.head.appendChild(styleSheet);

document.addEventListener('DOMContentLoaded', function() {
    const token = localStorage.getItem('token');
    const userId = localStorage.getItem('userId');
    if (token && userId) {
        connectWebSocket(userId, token);
        startHeartbeat();
    }
});