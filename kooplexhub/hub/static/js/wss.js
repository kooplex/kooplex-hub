class ManagedWebSocket {
    constructor(endpoint, callbacks = {}, reconnectInterval = 3000) {
        this.endpoint = endpoint;
        this.callbacks = callbacks; // e.g., { onOpen, onMessage, onClose, onError }
        this.reconnectInterval = reconnectInterval;
        this.socket = null;
        this.isManuallyClosed = false;
        this.pendingMessages = []; // Store messages to send when reconnected
        this.connect();
    }

    connect() {
        this.socket = new WebSocket(this.endpoint);

        this.socket.onopen = () => {
            console.log('WebSocket connection opened: ' + this.endpoint);
            if (this.callbacks.onOpen) this.callbacks.onOpen();

            // Flush pending messages
            this.pendingMessages.forEach((message) => this.socket.send(message));
            this.pendingMessages = [];
        };

        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log("Received attributes:", Object.keys(data));
            if (data['feedback']) {
              feedback(data['feedback']);
            }
            //if (this.callbacks.onMessage) this.callbacks.onMessage(event);
            if (this.callbacks.onMessage) this.callbacks.onMessage(data);
        };

        this.socket.onclose = () => {
            console.log('WebSocket connection closed to ' + this.endpoint);
            if (this.callbacks.onClose) this.callbacks.onClose();

            // Attempt reconnection if not manually closed
            if (!this.isManuallyClosed) {
                setTimeout(() => this.connect(), this.reconnectInterval);
            }
        };

        this.socket.onerror = (error) => {
		$("#oopses").text(error)//FIXME : remove it
            console.error('WebSocket error:', error, this.endpoint);
            if (this.callbacks.onError) this.callbacks.onError(error);
        };
    }

    send(data) {
        if (this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(data);
        } else {
		$("#oopses").text(this.socket.readyState)//FIXME : remove it
            console.warn('WebSocket ${this.endpoint} is not ready. Attempting to reconnect...');
            this.pendingMessages.push(data); // Store the message for later
            if (this.socket.readyState === WebSocket.CLOSED) {
                this.connect(); // Reconnect if the socket is closed
            }
        }
    }

    close() {
        this.isManuallyClosed = true;
        this.socket.close();
    }
}

