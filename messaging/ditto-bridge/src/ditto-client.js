/**
 * Eclipse Ditto Client
 * Handles communication with Eclipse Ditto for digital twin management
 */

const axios = require('axios');
const WebSocket = require('ws');
const EventEmitter = require('events');

class DittoClient extends EventEmitter {
    constructor(config) {
        super();
        this.config = config;
        this.baseUrl = `${config.protocol}://${config.host}:${config.port}`;
        this.apiVersion = config.apiVersion || 2;
        this.namespace = config.namespace;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 5000;
        this.connected = false;

        // Setup axios instance with auth
        this.api = axios.create({
            baseURL: `${this.baseUrl}/api/${this.apiVersion}`,
            timeout: 10000,
            headers: {
                'Content-Type': 'application/json'
            },
            auth: {
                username: config.username,
                password: config.password
            }
        });
    }

    async connect() {
        try {
            // Test HTTP connection
            await this.testConnection();
            console.log('✓ Ditto HTTP API connection successful');

            // Setup WebSocket connection for real-time updates
            if (this.config.useWebSocket) {
                await this.connectWebSocket();
            }

            this.connected = true;
            this.reconnectAttempts = 0;
            this.emit('connected');

        } catch (error) {
            console.error('Ditto connection failed:', error.message);
            throw error;
        }
    }

    async testConnection() {
        try {
            await this.api.get('/');
            return true;
        } catch (error) {
            if (error.response) {
                throw new Error(`Ditto API error: ${error.response.status} - ${error.response.statusText}`);
            } else if (error.request) {
                throw new Error('No response from Ditto server - check if it\'s running');
            } else {
                throw new Error(`Connection error: ${error.message}`);
            }
        }
    }

    async connectWebSocket() {
        return new Promise((resolve, reject) => {
            const wsUrl = `${this.config.wsProtocol}://${this.config.host}:${this.config.port}/ws/${this.apiVersion}`;
            const auth = Buffer.from(`${this.config.username}:${this.config.password}`).toString('base64');

            this.ws = new WebSocket(wsUrl, {
                headers: {
                    'Authorization': `Basic ${auth}`
                }
            });

            this.ws.on('open', () => {
                console.log('✓ Ditto WebSocket connected');
                
                // Subscribe to thing changes
                const subscription = {
                    topic: `${this.namespace}/things/twin/events`,
                    options: {
                        filter: `like(thingId,"${this.namespace}:*")`
                    }
                };
                
                this.ws.send(JSON.stringify(subscription));
                resolve();
            });

            this.ws.on('message', (data) => {
                try {
                    const message = JSON.parse(data);
                    this.handleWebSocketMessage(message);
                } catch (error) {
                    console.error('Error parsing WebSocket message:', error.message);
                }
            });

            this.ws.on('error', (error) => {
                console.error('WebSocket error:', error.message);
                reject(error);
            });

            this.ws.on('close', () => {
                console.warn('WebSocket disconnected');
                this.connected = false;
                this.attemptReconnect();
            });

            setTimeout(() => reject(new Error('WebSocket connection timeout')), 10000);
        });
    }

    handleWebSocketMessage(message) {
        // Handle different message types
        if (message.topic && message.topic.includes('/things/twin/events')) {
            this.emit('thing-changed', message);
        }
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
            
            setTimeout(() => {
                this.connectWebSocket().catch(error => {
                    console.error('Reconnection failed:', error.message);
                });
            }, this.reconnectDelay);
        } else {
            console.error('Max reconnection attempts reached');
            this.emit('connection-lost');
        }
    }

    // =========================================================================
    // THING OPERATIONS
    // =========================================================================

    async createThing(thingData) {
        try {
            const response = await this.api.put(`/things/${thingData.thingId}`, thingData);
            return response.data;
        } catch (error) {
            this.handleApiError('createThing', error);
        }
    }

    async updateThing(thingData) {
        try {
            const response = await this.api.put(`/things/${thingData.thingId}`, thingData);
            return response.data;
        } catch (error) {
            // If thing doesn't exist, create it
            if (error.response && error.response.status === 404) {
                return await this.createThing(thingData);
            }
            this.handleApiError('updateThing', error);
        }
    }

    async getThing(thingId) {
        try {
            const response = await this.api.get(`/things/${thingId}`);
            return response.data;
        } catch (error) {
            if (error.response && error.response.status === 404) {
                return null;
            }
            this.handleApiError('getThing', error);
        }
    }

    async deleteThing(thingId) {
        try {
            await this.api.delete(`/things/${thingId}`);
            return true;
        } catch (error) {
            this.handleApiError('deleteThing', error);
        }
    }

    async listThings(filter = null) {
        try {
            const params = {};
            if (filter) {
                params.filter = filter;
            }
            
            const response = await this.api.get('/things', { params });
            return response.data;
        } catch (error) {
            this.handleApiError('listThings', error);
        }
    }

    // =========================================================================
    // ATTRIBUTES OPERATIONS
    // =========================================================================

    async updateAttributes(thingId, attributes) {
        try {
            const response = await this.api.put(`/things/${thingId}/attributes`, attributes);
            return response.data;
        } catch (error) {
            this.handleApiError('updateAttributes', error);
        }
    }

    async updateAttribute(thingId, attributePath, value) {
        try {
            const response = await this.api.put(
                `/things/${thingId}/attributes/${attributePath}`, 
                value
            );
            return response.data;
        } catch (error) {
            this.handleApiError('updateAttribute', error);
        }
    }

    // =========================================================================
    // FEATURES OPERATIONS
    // =========================================================================

    async updateFeature(thingId, featureId, featureData) {
        try {
            const response = await this.api.put(
                `/things/${thingId}/features/${featureId}`,
                featureData
            );
            return response.data;
        } catch (error) {
            this.handleApiError('updateFeature', error);
        }
    }

    async updateFeatureProperty(thingId, featureId, propertyPath, value) {
        try {
            const response = await this.api.put(
                `/things/${thingId}/features/${featureId}/properties/${propertyPath}`,
                value
            );
            return response.data;
        } catch (error) {
            this.handleApiError('updateFeatureProperty', error);
        }
    }

    async getFeature(thingId, featureId) {
        try {
            const response = await this.api.get(`/things/${thingId}/features/${featureId}`);
            return response.data;
        } catch (error) {
            if (error.response && error.response.status === 404) {
                return null;
            }
            this.handleApiError('getFeature', error);
        }
    }

    // =========================================================================
    // MESSAGES
    // =========================================================================

    async sendMessage(thingId, subject, payload, timeout = 10) {
        try {
            const response = await this.api.post(
                `/things/${thingId}/inbox/messages/${subject}?timeout=${timeout}`,
                payload
            );
            return response.data;
        } catch (error) {
            this.handleApiError('sendMessage', error);
        }
    }

    // =========================================================================
    // SEARCH
    // =========================================================================

    async searchThings(filter, options = {}) {
        try {
            const params = { filter };
            
            if (options.namespaces) {
                params.namespaces = options.namespaces.join(',');
            }
            if (options.fields) {
                params.fields = options.fields.join(',');
            }
            if (options.sort) {
                params.option = `sort(${options.sort})`;
            }
            if (options.limit) {
                params.option = `${params.option || ''},limit(0,${options.limit})`;
            }

            const response = await this.api.get('/search/things', { params });
            return response.data;
        } catch (error) {
            this.handleApiError('searchThings', error);
        }
    }

    // =========================================================================
    // POLICIES
    // =========================================================================

    async createPolicy(policyId, policyData) {
        try {
            const response = await this.api.put(`/policies/${policyId}`, policyData);
            return response.data;
        } catch (error) {
            this.handleApiError('createPolicy', error);
        }
    }

    async getPolicy(policyId) {
        try {
            const response = await this.api.get(`/policies/${policyId}`);
            return response.data;
        } catch (error) {
            if (error.response && error.response.status === 404) {
                return null;
            }
            this.handleApiError('getPolicy', error);
        }
    }

    // =========================================================================
    // UTILITY METHODS
    // =========================================================================

    async createGridTwinIfNotExists(gridId, gridConfig) {
        const thingId = `${this.namespace}:grid-${gridId}`;
        
        // Check if thing exists
        const existingThing = await this.getThing(thingId);
        if (existingThing) {
            console.log(`Grid twin ${thingId} already exists`);
            return existingThing;
        }

        // Create policy first
        const policyId = `${this.namespace}:grid-policy`;
        const existingPolicy = await this.getPolicy(policyId);
        
        if (!existingPolicy) {
            const policy = {
                entries: {
                    DEFAULT: {
                        subjects: {
                            'nginx:ditto': { type: 'nginx basic auth user' }
                        },
                        resources: {
                            'thing:/': {
                                grant: ['READ', 'WRITE'],
                                revoke: []
                            },
                            'policy:/': {
                                grant: ['READ', 'WRITE'],
                                revoke: []
                            },
                            'message:/': {
                                grant: ['READ', 'WRITE'],
                                revoke: []
                            }
                        }
                    }
                }
            };
            
            await this.createPolicy(policyId, policy);
            console.log(`✓ Created policy ${policyId}`);
        }

        // Create thing
        const thingData = {
            thingId: thingId,
            policyId: policyId,
            attributes: {
                gridId: gridId,
                zoneType: gridConfig.zone_type || 'stand',
                area_sqm: gridConfig.area_sqm || 750,
                capacity: gridConfig.capacity || 200,
                location: gridConfig.location || {},
                created: new Date().toISOString()
            },
            features: {
                crowdMonitoring: {
                    properties: {
                        peopleCount: 0,
                        crowdDensity: {},
                        densityLevel: 'normal'
                    }
                },
                behaviorAnalysis: {
                    properties: {
                        alerts: [],
                        normalConfidence: 1.0
                    }
                },
                emergencyDetection: {
                    properties: {
                        status: 'clear',
                        type: null,
                        confidence: 0
                    }
                },
                deviceHealth: {
                    properties: {
                        healthScore: 100,
                        cpuTemperature: 0,
                        cpuUsage: 0,
                        memoryUsage: 0,
                        connectivity: false
                    }
                },
                alerts: {
                    properties: {
                        latestAlert: null,
                        alertCount: 0,
                        lastAlertTime: null
                    }
                }
            }
        };

        const thing = await this.createThing(thingData);
        console.log(`✓ Created grid twin ${thingId}`);
        
        return thing;
    }

    handleApiError(operation, error) {
        if (error.response) {
            const msg = `Ditto API error in ${operation}: ${error.response.status} - ${JSON.stringify(error.response.data)}`;
            console.error(msg);
            throw new Error(msg);
        } else if (error.request) {
            const msg = `No response from Ditto in ${operation}`;
            console.error(msg);
            throw new Error(msg);
        } else {
            console.error(`Error in ${operation}:`, error.message);
            throw error;
        }
    }

    async disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        this.connected = false;
        this.emit('disconnected');
    }

    isConnected() {
        return this.connected;
    }
}

module.exports = DittoClient;