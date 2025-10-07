#!/usr/bin/env node
/**
 * DHSILED Eclipse Ditto Bridge
 * Bridges MQTT messages to Eclipse Ditto for digital twin synchronization
 */

const MQTTHandler = require('./mqtt-handler');
const DittoClient = require('./ditto-client');
const config = require('../config/bridge-config.json');

class DittoBridge {
    constructor() {
        this.mqttHandler = new MQTTHandler(config.mqtt);
        this.dittoClient = new DittoClient(config.ditto);
        this.messageQueue = [];
        this.isProcessing = false;
        this.stats = {
            messagesReceived: 0,
            messagesSent: 0,
            errors: 0,
            startTime: new Date()
        };
    }

    async start() {
        console.log('='.repeat(60));
        console.log('DHSIELD Ditto Bridge Starting...');
        console.log('='.repeat(60));

        try {
            // Initialize MQTT connection
            await this.mqttHandler.connect();
            console.log('✓ Connected to MQTT broker');

            // Initialize Ditto connection
            await this.dittoClient.connect();
            console.log('✓ Connected to Eclipse Ditto');

            // Setup message handlers
            this.setupMessageHandlers();

            // Start processing queue
            this.startQueueProcessor();

            console.log('\n✓ Bridge is running and forwarding messages');
            console.log('  MQTT → Ditto digital twins\n');

            // Log stats periodically
            setInterval(() => this.logStats(), 60000); // Every minute

        } catch (error) {
            console.error('✗ Failed to start bridge:', error.message);
            process.exit(1);
        }
    }

    setupMessageHandlers() {
        // Handle grid status updates
        this.mqttHandler.on('grid-status', async (gridId, data) => {
            this.stats.messagesReceived++;
            await this.updateGridTwin(gridId, data);
        });

        // Handle alerts
        this.mqttHandler.on('alert', async (gridId, data) => {
            this.stats.messagesReceived++;
            await this.updateAlertInTwin(gridId, data);
        });

        // Handle health updates
        this.mqttHandler.on('health', async (gridId, data) => {
            this.stats.messagesReceived++;
            await this.updateHealthInTwin(gridId, data);
        });

        // Handle connection status
        this.mqttHandler.on('connected', () => {
            console.log('✓ MQTT reconnected');
        });

        this.mqttHandler.on('disconnected', () => {
            console.warn('⚠ MQTT disconnected, will attempt reconnect...');
        });
    }

    async updateGridTwin(gridId, data) {
        try {
            const thingId = `${config.ditto.namespace}:grid-${gridId}`;

            // Transform MQTT data to Ditto thing format
            const twinData = {
                thingId: thingId,
                policyId: `${config.ditto.namespace}:grid-policy`,
                attributes: {
                    gridId: gridId,
                    lastUpdate: new Date().toISOString(),
                    zoneType: data.zone_type || 'stand',
                    location: data.location || {}
                },
                features: {
                    crowdMonitoring: {
                        properties: {
                            peopleCount: data.people_count || 0,
                            crowdDensity: data.crowd_density || {},
                            densityLevel: data.crowd_density?.level || 'normal',
                            peopleLocations: data.people_locations || []
                        }
                    },
                    behaviorAnalysis: {
                        properties: {
                            alerts: data.behavior_analysis?.alerts || [],
                            normalConfidence: data.behavior_analysis?.normal_behavior_confidence || 1.0
                        }
                    },
                    emergencyDetection: {
                        properties: {
                            status: data.emergency_detection?.status || 'clear',
                            type: data.emergency_detection?.type || null,
                            confidence: data.emergency_detection?.confidence || 0
                        }
                    },
                    performance: {
                        properties: {
                            processingTime: data.processing_time || 0,
                            modelPerformance: data.model_performance || {}
                        }
                    }
                }
            };

            // Send to Ditto
            await this.dittoClient.updateThing(twinData);
            this.stats.messagesSent++;

        } catch (error) {
            console.error(`Error updating grid twin ${gridId}:`, error.message);
            this.stats.errors++;
        }
    }

    async updateAlertInTwin(gridId, alertData) {
        try {
            const thingId = `${config.ditto.namespace}:grid-${gridId}`;

            // Update alerts feature
            await this.dittoClient.updateFeature(thingId, 'alerts', {
                properties: {
                    latestAlert: alertData,
                    alertCount: (await this.getAlertCount(thingId)) + 1,
                    lastAlertTime: new Date().toISOString()
                }
            });

            this.stats.messagesSent++;

            // If critical alert, trigger Ditto message
            if (alertData.severity === 'critical') {
                await this.dittoClient.sendMessage(thingId, 'critical-alert', alertData);
            }

        } catch (error) {
            console.error(`Error updating alert for ${gridId}:`, error.message);
            this.stats.errors++;
        }
    }

    async updateHealthInTwin(gridId, healthData) {
        try {
            const thingId = `${config.ditto.namespace}:grid-${gridId}`;

            // Update device health feature
            await this.dittoClient.updateFeature(thingId, 'deviceHealth', {
                properties: {
                    healthScore: healthData.health_score || 0,
                    cpuTemperature: healthData.cpu_temperature || 0,
                    cpuUsage: healthData.cpu_usage?.overall || 0,
                    memoryUsage: healthData.memory_usage?.percentage || 0,
                    connectivity: healthData.network_stats?.connectivity || false,
                    lastHealthCheck: new Date().toISOString(),
                    alerts: healthData.alerts || []
                }
            });

            this.stats.messagesSent++;

        } catch (error) {
            console.error(`Error updating health for ${gridId}:`, error.message);
            this.stats.errors++;
        }
    }

    async getAlertCount(thingId) {
        try {
            const thing = await this.dittoClient.getThing(thingId);
            return thing?.features?.alerts?.properties?.alertCount || 0;
        } catch {
            return 0;
        }
    }

    startQueueProcessor() {
        setInterval(async () => {
            if (this.messageQueue.length > 0 && !this.isProcessing) {
                this.isProcessing = true;
                const message = this.messageQueue.shift();
                
                try {
                    await this.processQueuedMessage(message);
                } catch (error) {
                    console.error('Error processing queued message:', error.message);
                }
                
                this.isProcessing = false;
            }
        }, 100);
    }

    async processQueuedMessage(message) {
        // Process any queued messages
        // Implementation depends on message type
    }

    logStats() {
        const uptime = Math.floor((new Date() - this.stats.startTime) / 1000);
        const uptimeStr = `${Math.floor(uptime / 3600)}h ${Math.floor((uptime % 3600) / 60)}m`;

        console.log('\n📊 Bridge Statistics:');
        console.log(`   Uptime: ${uptimeStr}`);
        console.log(`   Messages received: ${this.stats.messagesReceived}`);
        console.log(`   Messages sent to Ditto: ${this.stats.messagesSent}`);
        console.log(`   Errors: ${this.stats.errors}`);
        console.log(`   Queue size: ${this.messageQueue.length}`);
    }

    async stop() {
        console.log('\nShutting down bridge...');
        
        await this.mqttHandler.disconnect();
        await this.dittoClient.disconnect();
        
        this.logStats();
        console.log('✓ Bridge stopped gracefully\n');
    }
}

// Main execution
if (require.main === module) {
    const bridge = new DittoBridge();

    // Handle graceful shutdown
    process.on('SIGINT', async () => {
        await bridge.stop();
        process.exit(0);
    });

    process.on('SIGTERM', async () => {
        await bridge.stop();
        process.exit(0);
    });

    // Start the bridge
    bridge.start().catch(error => {
        console.error('Fatal error:', error);
        process.exit(1);
    });
}

module.exports = DittoBridge;