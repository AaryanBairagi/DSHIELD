/**
 * API Client for DHSILED Command Center
 * Handles REST API calls to backend server
 */

class ApiClient {
    constructor(baseUrl = 'http://localhost:5000/api') {
        this.baseUrl = baseUrl;
        this.defaultHeaders = {
            'Content-Type': 'application/json'
        };
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        
        const config = {
            method: options.method || 'GET',
            headers: {
                ...this.defaultHeaders,
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

            const data = await response.json();
            return data;

        } catch (error) {
            console.error(`API request failed: ${endpoint}`, error);
            throw error;
        }
    }

    // =========================================================================
    // GRID OPERATIONS
    // =========================================================================

    async getGrids() {
        return await this.request('/grids');
    }

    async getGrid(gridId) {
        return await this.request(`/grids/${gridId}`);
    }

    async getGridHistory(gridId, hours = 24) {
        return await this.request(`/grids/${gridId}/history?hours=${hours}`);
    }

    async sendGridCommand(gridId, command) {
        return await this.request(`/grids/${gridId}/command`, {
            method: 'POST',
            body: { command }
        });
    }

    // =========================================================================
    // ALERT OPERATIONS
    // =========================================================================

    async getAlerts(limit = 50, severity = null) {
        let endpoint = `/alerts?limit=${limit}`;
        if (severity) {
            endpoint += `&severity=${severity}`;
        }
        return await this.request(endpoint);
    }

    async getAlert(alertId) {
        return await this.request(`/alerts/${alertId}`);
    }

    async acknowledgeAlert(alertId, user = 'operator') {
        return await this.request(`/alerts/${alertId}/acknowledge`, {
            method: 'POST',
            body: { user }
        });
    }

    // =========================================================================
    // SYSTEM HEALTH
    // =========================================================================

    async getSystemHealth() {
        return await this.request('/health');
    }

    async getGridsHealth() {
        return await this.request('/health/grids');
    }

    // =========================================================================
    // ANALYTICS
    // =========================================================================

    async getOccupancyAnalytics() {
        return await this.request('/analytics/occupancy');
    }

    async getHeatmapData() {
        return await this.request('/analytics/heatmap');
    }

    async getTrends(hours = 24) {
        return await this.request(`/analytics/trends?hours=${hours}`);
    }

    // =========================================================================
    // SYSTEM COMMANDS
    // =========================================================================

    async broadcastCommand(command) {
        return await this.request('/system/broadcast', {
            method: 'POST',
            body: { command }
        });
    }

    // =========================================================================
    // UTILITY METHODS
    // =========================================================================

    setBaseUrl(url) {
        this.baseUrl = url;
    }

    setAuthToken(token) {
        this.defaultHeaders['Authorization'] = `Bearer ${token}`;
    }

    removeAuthToken() {
        delete this.defaultHeaders['Authorization'];
    }
}

export default ApiClient;