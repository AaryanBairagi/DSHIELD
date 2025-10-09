/**
 * Three.js Helper Functions
 * Utilities for 3D rendering and visualization
 */

import * as THREE from 'three';

/**
 * Create a basic stadium structure
 * @returns {THREE.Group} Stadium group
 */
export function createStadiumStructure() {
    const stadium = new THREE.Group();

    // Ground/Field
    const fieldGeometry = new THREE.CircleGeometry(90, 64);
    const fieldMaterial = new THREE.MeshStandardMaterial({ 
        color: 0x2a5934,
        side: THREE.DoubleSide
    });
    const field = new THREE.Mesh(fieldGeometry, fieldMaterial);
    field.rotation.x = -Math.PI / 2;
    field.position.y = -1;
    field.receiveShadow = true;
    stadium.add(field);

    // Stadium walls
    const wallGeometry = new THREE.CylinderGeometry(100, 100, 20, 64, 1, true);
    const wallMaterial = new THREE.MeshStandardMaterial({ 
        color: 0x888888,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.3
    });
    const walls = new THREE.Mesh(wallGeometry, wallMaterial);
    walls.position.y = 10;
    stadium.add(walls);

    return stadium;
}

/**
 * Create a grid zone mesh
 * @param {Object} config - Grid configuration
 * @returns {THREE.Mesh} Grid mesh
 */
export function createGridZone(config) {
    const { position, peopleCount, densityLevel, gridId } = config;
    
    const height = Math.max(2, peopleCount / 10);
    const geometry = new THREE.BoxGeometry(25, height, 30);
    
    const color = getDensityColor(densityLevel);
    const material = new THREE.MeshStandardMaterial({
        color: new THREE.Color(color),
        transparent: true,
        opacity: 0.7,
        emissive: new THREE.Color(color),
        emissiveIntensity: 0.2
    });
    
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(position.x, position.y + height / 2, position.z);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    mesh.userData = { gridId, peopleCount, densityLevel };
    
    return mesh;
}

/**
 * Get color for density level
 * @param {string} level - Density level
 * @returns {string} Hex color
 */
function getDensityColor(level) {
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
 * Create label sprite
 * @param {string} text - Label text
 * @returns {THREE.Sprite} Label sprite
 */
export function createTextLabel(text) {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    canvas.width = 256;
    canvas.height = 64;
    
    context.fillStyle = 'rgba(0, 0, 0, 0.7)';
    context.fillRect(0, 0, canvas.width, canvas.height);
    
    context.font = 'Bold 24px Arial';
    context.fillStyle = 'white';
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.fillText(text, canvas.width / 2, canvas.height / 2);
    
    const texture = new THREE.CanvasTexture(canvas);
    const spriteMaterial = new THREE.SpriteMaterial({ map: texture });
    const sprite = new THREE.Sprite(spriteMaterial);
    sprite.scale.set(10, 2.5, 1);
    
    return sprite;
}

/**
 * Create alert indicator
 * @param {string} severity - Alert severity
 * @returns {THREE.Mesh} Alert indicator
 */
export function createAlertIndicator(severity) {
    const geometry = new THREE.SphereGeometry(2, 16, 16);
    
    const colors = {
        critical: 0xff0000,
        high: 0xff6600,
        medium: 0xffaa00,
        low: 0x0088ff
    };
    
    const material = new THREE.MeshBasicMaterial({
        color: colors[severity] || colors.medium,
        transparent: true,
        opacity: 0.8
    });
    
    const indicator = new THREE.Mesh(geometry, material);
    return indicator;
}

/**
 * Animate pulsing effect
 * @param {THREE.Mesh} mesh - Mesh to animate
 * @param {number} speed - Animation speed
 */
export function addPulseAnimation(mesh, speed = 1) {
    const startScale = mesh.scale.clone();
    
    return (time) => {
        const scale = 1 + Math.sin(time * speed) * 0.1;
        mesh.scale.set(
            startScale.x * scale,
            startScale.y * scale,
            startScale.z * scale
        );
    };
}

/**
 * Create camera path for animation
 * @param {Array} points - Path points
 * @returns {THREE.CatmullRomCurve3} Camera path
 */
export function createCameraPath(points) {
    const vectors = points.map(p => new THREE.Vector3(p.x, p.y, p.z));
    return new THREE.CatmullRomCurve3(vectors, true);
}

/**
 * Calculate optimal camera position
 * @param {THREE.Box3} boundingBox - Scene bounding box
 * @returns {THREE.Vector3} Camera position
 */
export function calculateCameraPosition(boundingBox) {
    const center = new THREE.Vector3();
    boundingBox.getCenter(center);
    
    const size = new THREE.Vector3();
    boundingBox.getSize(size);
    
    const maxDim = Math.max(size.x, size.y, size.z);
    const fov = 50;
    const cameraDistance = maxDim / (2 * Math.tan((fov * Math.PI) / 360));
    
    return new THREE.Vector3(
        center.x,
        center.y + cameraDistance * 0.5,
        center.z + cameraDistance
    );
}