/**
 * MQTT Handler for Ditto Bridge
 * Subscribes to DHSILED MQTT topics and emits events
 */

const mqtt = require('mqtt');
const EventEmitter = require('events');

class MQTTHandler extends EventEmitter {
    constructor(config) {
        super();
        this.config = config;
        this.client = null;
        this.connected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
    }

    async connect() {
        return new Promise((resolve, reject) => {
            const options = {
                host: this.config.host,
                port: this.config.port,
                clientId: `dhsiled_ditto_bridge_${Date.now()}`,
                clean: true,
                reconnectPeriod: 5000,
                connectTimeout: 30000
            };

            // Add authentication if configured
            if (this.config.username && this.config.password) {
                options.username = this.config.username;
                options.password = this.config.password;
            }

            // Add SSL/TLS if configured
            if (this.config.ssl) {
                options.protocol = 'mqtts';
            }

            console.log(`Connecting to MQTT broker at ${this.config.host}:${this.config.port}...`);
            
            this.client = mqtt.connect(options);

            this.client.on('connect', () => {
                console.log('✓ MQTT connected successfully');
                this.connected = true;
                this.reconnectAttempts = 0;
                this.subscribeToTopics();
                this.emit('connected');
                resolve();
            });

            this.client.on('error', (error) => {
                console.error('MQTT error:', error.message);
                this.emit('error', error);
                if (!this.connected) {
                    reject(error);
                }
            });

            this.client.on('close', () => {
                if (this.connected) {
                    console.warn('MQTT connection closed');
                    this.connected = false;
                    this.emit('disconnected');
                }
            });

            this.client.on('reconnect', () => {
                this.reconnectAttempts++;
                console.log(`MQTT reconnecting... (attempt ${this.reconnectAttempts})`);
            });

            this.client.on('message', (topic, message) => {
                this.handleMessage(topic, message);
            });

            // Timeout
            setTimeout(() => {
                if (!this.connected) {
                    reject(new Error('MQTT connection timeout'));
                }
            }, 30000);
        });
    }

    subscribeToTopics() {
        const topics = [
            'dhsiled/grids/+/status',
            'dhsiled/grids/+/alerts',
            'dhsiled/grids/+/health',
            'dhsiled/system/+',
        ];

        topics.forEach(topic => {
            this.client.subscribe(topic, { qos: 1 }, (error) => {
                if (error) {
                    console.error(`Failed to subscribe to ${topic}:`, error.message);
                } else {
                    console.log(`✓ Subscribed to ${topic}`);
                }
            });
        });
    }

    handleMessage(topic, message) {
        try {
            const data = JSON.parse(message.toString());
            const parts = topic.split('/');

            // Extract grid ID if present
            const gridId = parts[2];
            const messageType = parts[3];

            switch (messageType) {
                case 'status':
                    this.emit('grid-status', gridId, data);
                    break;
                
                case 'alerts':
                    this.emit('alert', gridId, data);
                    break;
                
                case 'health':
                    this.emit('health', gridId, data);
                    break;
                
                default:
                    this.emit('message', topic, data);
            }

        } catch (error) {
            console.error('Error handling MQTT message:', error.message);
            console.error('Topic:', topic);
            console.error('Message:', message.toString());
        }
    }

    publish(topic, payload, options = {}) {
        return new Promise((resolve, reject) => {
            if (!this.connected) {
                reject(new Error('MQTT not connected'));
                return;
            }

            const message = typeof payload === 'string' ? payload : JSON.stringify(payload);
            
            this.client.publish(topic, message, { qos: options.qos || 1 }, (error) => {
                if (error) {
                    reject(error);
                } else {
                    resolve();
                }
            });
        });
    }

    async disconnect() {
        return new Promise((resolve) => {
            if (this.client) {
                this.client.end(false, () => {
                    console.log('MQTT disconnected');
                    this.connected = false;
                    resolve();
                });
            } else {
                resolve();
            }
        });
    }

    isConnected() {
        return this.connected;
    }
}

module.exports = MQTTHandler;