/**
 * AEGIS Real-time WebSocket Client
 * Maintains live event stream connection and notifies UI components.
 */

class AEGISWebSocket {
    constructor() {
        this.socket = null;
        this.listeners = new Set();
        this.reconnectInterval = 3000;
        this.pingTimer = null;
        this.isConnected = false;
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/events`;

        try {
            this.socket = new WebSocket(wsUrl);

            this.socket.onopen = () => {
                this.isConnected = true;
                this.updateUIStatus(true);
                console.log("[AEGIS WS] Connected to live event stream");

                // Start periodic ping to prevent idle disconnect
                this.pingTimer = setInterval(() => {
                    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                        this.socket.send("ping");
                    }
                }, 20000);
            };

            this.socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'pong') return;
                    this.notifyListeners(data);
                } catch (e) {
                    console.warn("[AEGIS WS] Non-JSON payload:", event.data);
                }
            };

            this.socket.onclose = () => {
                this.isConnected = false;
                this.updateUIStatus(false);
                if (this.pingTimer) clearInterval(this.pingTimer);
                console.warn("[AEGIS WS] Connection closed. Reconnecting in 3s...");
                setTimeout(() => this.connect(), this.reconnectInterval);
            };

            this.socket.onerror = (err) => {
                console.error("[AEGIS WS] Error:", err);
            };
        } catch (e) {
            console.error("[AEGIS WS] Connection initiation failed:", e);
            setTimeout(() => this.connect(), this.reconnectInterval);
        }
    }

    subscribe(callback) {
        this.listeners.add(callback);
        return () => this.listeners.delete(callback);
    }

    notifyListeners(payload) {
        this.listeners.forEach(cb => {
            try {
                cb(payload);
            } catch (err) {
                console.error("[AEGIS WS] Error in listener:", err);
            }
        });
    }

    updateUIStatus(connected) {
        const dot = document.getElementById('ws-pulse-dot');
        const text = document.getElementById('ws-status-text');
        if (dot && text) {
            if (connected) {
                dot.className = 'pulse-dot';
                text.textContent = 'LIVE FEED ONLINE';
            } else {
                dot.className = 'pulse-dot disconnected';
                text.textContent = 'CONNECTING...';
            }
        }
    }
}

window.aegisWS = new AEGISWebSocket();
