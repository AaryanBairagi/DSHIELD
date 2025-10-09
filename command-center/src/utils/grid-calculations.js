/**
 * Grid Calculation Utilities
 * Helper functions for grid layout and calculations
 */

/**
 * Calculate grid position in 3D space
 * @param {number} gridIndex - Grid index (0-47)
 * @param {number} totalGrids - Total number of grids
 * @returns {Object} Position {x, y, z}
 */
export function calculateGridPosition(gridIndex, totalGrids = 48) {
    const radius = 80; // Stadium radius
    const angleStep = (2 * Math.PI) / totalGrids;
    const angle = gridIndex * angleStep;
    
    return {
        x: Math.cos(angle) * radius,
        y: 5, // Ground level
        z: Math.sin(angle) * radius
    };
}

/**
 * Calculate crowd density level
 * @param {number} peopleCount - Number of people
 * @param {number} capacity - Grid capacity
 * @returns {string} Density level
 */
export function calculateDensityLevel(peopleCount, capacity = 200) {
    const ratio = peopleCount / capacity;
    
    if (ratio <= 0.3) return 'low';
    if (ratio <= 0.5) return 'normal';
    if (ratio <= 0.75) return 'moderate';
    if (ratio <= 0.9) return 'high';
    return 'critical';
}

/**
 * Calculate density percentage
 * @param {number} peopleCount - Number of people
 * @param {number} areaSqm - Area in square meters
 * @returns {number} Density percentage
 */
export function calculateDensityPercentage(peopleCount, areaSqm = 750) {
    const densityPerSqm = peopleCount / areaSqm;
    const percentage = Math.min((densityPerSqm / 4.0) * 100, 100);
    return Math.round(percentage * 10) / 10;
}

/**
 * Get color for density level
 * @param {string} level - Density level
 * @returns {string} Hex color
 */
export function getDensityColor(level) {
    const colors = {
        low: '#4ade80',
        normal: '#fbbf24',
        moderate: '#fb923c',
        high: '#f87171',
        critical: '#dc2626'
    };
    return colors[level] || colors.normal;
}

/**
 * Calculate grid statistics
 * @param {Object} gridStates - All grid states
 * @returns {Object} Statistics
 */
export function calculateGridStatistics(gridStates) {
    const stats = {
        totalGrids: 0,
        onlineGrids: 0,
        offlineGrids: 0,
        totalPeople: 0,
        averageDensity: 0,
        densityDistribution: {
            low: 0,
            normal: 0,
            moderate: 0,
            high: 0,
            critical: 0
        }
    };

    Object.values(gridStates).forEach(grid => {
        stats.totalGrids++;
        
        if (grid.status !== 'offline') {
            stats.onlineGrids++;
        } else {
            stats.offlineGrids++;
        }
        
        stats.totalPeople += grid.people_count || 0;
        
        const level = grid.crowd_density?.level || 'normal';
        stats.densityDistribution[level]++;
    });

    if (stats.onlineGrids > 0) {
        stats.averageDensity = Math.round(stats.totalPeople / stats.onlineGrids);
    }

    return stats;
}

/**
 * Format time ago
 * @param {string} timestamp - ISO timestamp
 * @returns {string} Formatted time
 */
export function formatTimeAgo(timestamp) {
    const now = new Date();
    const then = new Date(timestamp);
    const seconds = Math.floor((now - then) / 1000);

    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
}

/**
 * Generate grid layout for stadium
 * @param {number} totalGrids - Total number of grids
 * @returns {Array} Grid layout array
 */
export function generateStadiumLayout(totalGrids = 48) {
    const layout = [];
    
    for (let i = 0; i < totalGrids; i++) {
        const gridId = `G${String(i + 1).padStart(2, '0')}`;
        const position = calculateGridPosition(i, totalGrids);
        
        layout.push({
            gridId,
            position,
            zoneType: i < 24 ? 'stand' : 'stand', // Can be customized
            capacity: 200
        });
    }
    
    return layout;
}

/**
 * Calculate nearest grid to a point
 * @param {Object} point - Point {x, y, z}
 * @param {Object} gridStates - All grid states
 * @returns {string} Nearest grid ID
 */
export function getNearestGrid(point, gridStates) {
    let nearestGrid = null;
    let minDistance = Infinity;

    Object.entries(gridStates).forEach(([gridId, grid]) => {
        const pos = grid.location?.position || { x: 0, y: 0, z: 0 };
        const distance = Math.sqrt(
            Math.pow(point.x - pos.x, 2) +
            Math.pow(point.y - pos.y, 2) +
            Math.pow(point.z - pos.z, 2)
        );

        if (distance < minDistance) {
            minDistance = distance;
            nearestGrid = gridId;
        }
    });

    return nearestGrid;
}