/**
 * Eclipse Ditto Client for Command Center
 * Interacts with Ditto digital twins
 */

class DittoClient {
    constructor(baseUrl = 'http://localhost:8080/api/2', username = 'ditto', password = 'ditto') {
        this.baseUrl = baseUrl;
        this.username = username;
        this.password = password;
        this.authHeader = 'Basic ' + btoa(`${username}:${password}`);
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        
        const config = {
            method: options.method || 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': this.authHeader,
                ...options.headers
            }
        };

        if (options.body) {
            config.body = JSON.stringify(options.body);
        }

        try {
            const response = await fetch(url, config);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            // Handle empty responses
            const text = await response.text();
            return text ? JSON.parse(text) : null;

        } catch (error) {
            console.error(`Ditto request failed: ${endpoint}`, error);
            throw error;
        }
    }

    // =========================================================================
    // THING OPERATIONS
    // =========================================================================

    async getThing(thingId) {
        return await this.request(`/things/${thingId}`);
    }

    async listThings(namespace = 'org.dhsiled') {
        return await this.request(`/things?namespaces=${namespace}`);
    }

    async searchThings(filter) {
        return await this.request(`/search/things?filter=${encodeURIComponent(filter)}`);
    }

    async getThingAttribute(thingId, attributePath) {
        return await this.request(`/things/${thingId}/attributes/${attributePath}`);
    }

    async getThingFeature(thingId, featureId) {
        return await this.request(`/things/${thingId}/features/${featureId}`);
    }

    async getThingFeatureProperty(thingId, featureId, propertyPath) {
        return await this.request(`/things/${thingId}/features/${featureId}/properties/${propertyPath}`);
    }

    // =========================================================================
    // GRID TWIN OPERATIONS
    // =========================================================================

    async getGridTwin(gridId) {
        const thingId = `org.dhsiled:grid-${gridId}`;
        return await this.getThing(thingId);
    }

    async getAllGridTwins() {
        return await this.searchThings('like(thingId,"org.dhsiled:grid-*")');
    }

    async getGridCrowdData(gridId) {
        const thingId = `org.dhsiled:grid-${gridId}`;
        return await this.getThingFeature(thingId, 'crowdMonitoring');
    }

    async getGridHealthData(gridId) {
        const thingId = `org.dhsiled:grid-${gridId}`;
        return await this.getThingFeature(thingId, 'deviceHealth');
    }

    async getGridAlerts(gridId) {
        const thingId = `org.dhsiled:grid-${gridId}`;
        return await this.getThingFeature(thingId, 'alerts');
    }

    // =========================================================================
    // ANALYTICS
    // =========================================================================

    async getStadiumOccupancy() {
        try {
            const grids = await this.getAllGridTwins();
            
            let totalPeople = 0;
            const gridData = [];

            if (grids && grids.items) {
                for (const grid of grids.items) {
                    const peopleCount = grid.features?.crowdMonitoring?.properties?.peopleCount || 0;
                    totalPeople += peopleCount;
                    
                    gridData.push({
                        gridId: grid.attributes?.gridId,
                        peopleCount: peopleCount,
                        densityLevel: grid.features?.crowdMonitoring?.properties?.densityLevel,
                        location: grid.attributes?.location
                    });
                }
            }

            return {
                totalPeople,
                gridCount: gridData.length,
                grids: gridData
            };

        } catch (error) {
            console.error('Error getting stadium occupancy:', error);
            throw error;
        }
    }

    async getHighDensityGrids(threshold = 'high') {
        const filter = `and(like(thingId,"org.dhsiled:grid-*"),eq(features/crowdMonitoring/properties/densityLevel,"${threshold}"))`;
        return await this.searchThings(filter);
    }

    async getUnhealthyGrids(healthScoreThreshold = 70) {
        const filter = `and(like(thingId,"org.dhsiled:grid-*"),lt(features/deviceHealth/properties/healthScore,${healthScoreThreshold}))`;
        return await this.searchThings(filter);
    }

    // =========================================================================
    // WEBSOCKET SUBSCRIPTION
    // =========================================================================

    connectWebSocket(onMessage) {
        const wsUrl = this.baseUrl.replace('http', 'ws').replace('/api/2', '/ws/2');
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('✓ Connected to Ditto WebSocket');
            
            // Subscribe to all grid thing changes
            const subscription = {
                topic: 'org.dhsiled/things/twin/events',
                options: {
                    filter: 'like(thingId,"org.dhsiled:grid-*")'
                }
            };
            
            ws.send(JSON.stringify(subscription));
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                onMessage(data);
            } catch (error) {
                console.error('Error parsing Ditto WebSocket message:', error);
            }
        };

        ws.onerror = (error) => {
            console.error('Ditto WebSocket error:', error);
        };

        ws.onclose = () => {
            console.log('Ditto WebSocket closed');
        };

        return ws;
    }
}

export default DittoClient;