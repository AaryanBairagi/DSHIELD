#!/usr/bin/env python3
"""
DHSILED Backend API Server
REST API for historical data, analytics, and system management
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import json
import os
from datetime import datetime, timedelta
import paho.mqtt.client as mqtt
from threading import Thread
import time

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# In-memory storage (replace with database in production)
grid_states = {}
alert_history = []
health_history = []
analytics_cache = {}

# MQTT client for receiving data
mqtt_client = None

################################################################################
# MQTT INTEGRATION
################################################################################

def on_mqtt_message(client, userdata, message):
    """Handle incoming MQTT messages"""
    try:
        topic = message.topic
        payload = json.loads(message.payload.decode())
        
        if 'status' in topic:
            grid_id = topic.split('/')[2]
            grid_states[grid_id] = payload
            
        elif 'alerts' in topic:
            payload['received_at'] = datetime.utcnow().isoformat()
            alert_history.append(payload)
            if len(alert_history) > 1000:
                alert_history.pop(0)
                
        elif 'health' in topic:
            grid_id = topic.split('/')[2]
            payload['grid_id'] = grid_id
            health_history.append(payload)
            if len(health_history) > 500:
                health_history.pop(0)
                
    except Exception as e:
        print(f"Error processing MQTT message: {e}")

def start_mqtt_client():
    """Start MQTT client in background thread"""
    global mqtt_client
    
    mqtt_client = mqtt.Client(client_id="dhsiled_api_server")
    mqtt_client.on_message = on_mqtt_message
    
    try:
        mqtt_client.connect("localhost", 1883, 60)
        mqtt_client.subscribe("dhsiled/#")
        mqtt_client.loop_start()
        print("✓ MQTT client connected to broker")
    except Exception as e:
        print(f"✗ MQTT connection failed: {e}")

################################################################################
# API ENDPOINTS - GRID DATA
################################################################################

@app.route('/api/grids', methods=['GET'])
def get_all_grids():
    """Get status of all grids"""
    return jsonify({
        'success': True,
        'count': len(grid_states),
        'grids': grid_states,
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/api/grids/<grid_id>', methods=['GET'])
def get_grid(grid_id):
    """Get status of specific grid"""
    if grid_id in grid_states:
        return jsonify({
            'success': True,
            'grid': grid_states[grid_id]
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Grid not found'
        }), 404

@app.route('/api/grids/<grid_id>/history', methods=['GET'])
def get_grid_history(grid_id):
    """Get historical data for specific grid"""
    hours = int(request.args.get('hours', 24))
    
    # Generate mock history data
    history = []
    current_time = datetime.utcnow()
    
    for i in range(hours * 12):
        timestamp = current_time - timedelta(minutes=i*5)
        history.append({
            'timestamp': timestamp.isoformat(),
            'people_count': 50 + (i % 30),
            'density': 0.5 + (i % 20) * 0.01
        })
    
    return jsonify({
        'success': True,
        'grid_id': grid_id,
        'period_hours': hours,
        'data_points': len(history),
        'history': history[::-1]
    })

################################################################################
# API ENDPOINTS - ALERTS
################################################################################

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """Get all alerts"""
    limit = int(request.args.get('limit', 50))
    severity = request.args.get('severity', None)
    
    alerts = alert_history[-limit:]
    
    if severity:
        alerts = [a for a in alerts if a.get('severity') == severity]
    
    return jsonify({
        'success': True,
        'count': len(alerts),
        'alerts': alerts[::-1]
    })

@app.route('/api/alerts/<alert_id>', methods=['GET'])
def get_alert(alert_id):
    """Get specific alert by ID"""
    alert = next((a for a in alert_history if a.get('id') == alert_id), None)
    
    if alert:
        return jsonify({
            'success': True,
            'alert': alert
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Alert not found'
        }), 404

@app.route('/api/alerts/<alert_id>/acknowledge', methods=['POST'])
def acknowledge_alert(alert_id):
    """Acknowledge an alert"""
    alert = next((a for a in alert_history if a.get('id') == alert_id), None)
    
    if alert:
        alert['acknowledged'] = True
        alert['acknowledged_at'] = datetime.utcnow().isoformat()
        alert['acknowledged_by'] = request.json.get('user', 'system')
        
        return jsonify({
            'success': True,
            'message': 'Alert acknowledged'
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Alert not found'
        }), 404

################################################################################
# API ENDPOINTS - SYSTEM HEALTH
################################################################################

@app.route('/api/health', methods=['GET'])
def get_system_health():
    """Get overall system health"""
    total_grids = len(grid_states)
    online_grids = sum(1 for g in grid_states.values() if g.get('status') != 'offline')
    
    critical_alerts = sum(1 for a in alert_history[-100:] if a.get('severity') == 'critical')
    
    return jsonify({
        'success': True,
        'system_status': 'operational' if online_grids > 0 else 'offline',
        'total_grids': total_grids,
        'online_grids': online_grids,
        'offline_grids': total_grids - online_grids,
        'recent_critical_alerts': critical_alerts,
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/api/health/grids', methods=['GET'])
def get_grids_health():
    """Get health status of all grid devices"""
    return jsonify({
        'success': True,
        'count': len(health_history),
        'health_data': health_history[-50:]
    })

################################################################################
# API ENDPOINTS - ANALYTICS
################################################################################

@app.route('/api/analytics/occupancy', methods=['GET'])
def get_occupancy_analytics():
    """Get stadium occupancy analytics"""
    total_people = sum(g.get('people_count', 0) for g in grid_states.values())
    
    density_levels = {
        'normal': 0,
        'moderate': 0,
        'high': 0,
        'critical': 0
    }
    
    for grid in grid_states.values():
        level = grid.get('crowd_density', {}).get('level', 'normal')
        density_levels[level] = density_levels.get(level, 0) + 1
    
    return jsonify({
        'success': True,
        'total_people': total_people,
        'active_grids': len(grid_states),
        'density_distribution': density_levels,
        'average_density': total_people / max(len(grid_states), 1),
        'timestamp': datetime.utcnow().isoformat()
    })

@app.route('/api/analytics/heatmap', methods=['GET'])
def get_heatmap_data():
    """Get crowd density heatmap data"""
    heatmap_data = []
    
    for grid_id, grid_data in grid_states.items():
        position = grid_data.get('position', {})
        heatmap_data.append({
            'grid_id': grid_id,
            'x': position.get('x', 0),
            'y': position.get('y', 0),
            'z': position.get('z', 0),
            'people_count': grid_data.get('people_count', 0),
            'density': grid_data.get('crowd_density', {}).get('percentage', 0)
        })
    
    return jsonify({
        'success': True,
        'data': heatmap_data
    })

@app.route('/api/analytics/trends', methods=['GET'])
def get_trends():
    """Get crowd trends over time"""
    hours = int(request.args.get('hours', 24))
    
    trends = []
    current_time = datetime.utcnow()
    
    for i in range(hours * 6):
        timestamp = current_time - timedelta(minutes=i*10)
        trends.append({
            'timestamp': timestamp.isoformat(),
            'total_people': 500 + (i % 200),
            'average_density': 0.4 + (i % 30) * 0.01
        })
    
    return jsonify({
        'success': True,
        'period_hours': hours,
        'trends': trends[::-1]
    })

################################################################################
# API ENDPOINTS - COMMANDS
################################################################################

@app.route('/api/grids/<grid_id>/command', methods=['POST'])
def send_grid_command(grid_id):
    """Send command to specific grid"""
    command = request.json.get('command')
    
    if not command:
        return jsonify({
            'success': False,
            'error': 'Command required'
        }), 400
    
    topic = f"dhsiled/grids/{grid_id}/commands"
    payload = json.dumps(request.json)
    
    try:
        if mqtt_client:
            mqtt_client.publish(topic, payload)
            return jsonify({
                'success': True,
                'message': f'Command sent to {grid_id}'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'MQTT client not connected'
            }), 503
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/system/broadcast', methods=['POST'])
def broadcast_command():
    """Broadcast command to all grids"""
    command = request.json.get('command')
    
    if not command:
        return jsonify({
            'success': False,
            'error': 'Command required'
        }), 400
    
    topic = "dhsiled/system/broadcast"
    payload = json.dumps(request.json)
    
    try:
        if mqtt_client:
            mqtt_client.publish(topic, payload)
            return jsonify({
                'success': True,
                'message': 'Command broadcasted to all grids'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'MQTT client not connected'
            }), 503
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

################################################################################
# ERROR HANDLERS
################################################################################

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

################################################################################
# MAIN
################################################################################

if __name__ == '__main__':
    print("="*60)
    print("DHSILED Backend API Server")
    print("="*60)
    
    # Start MQTT client
    start_mqtt_client()
    
    # Start Flask server
    print(f"\n✓ API Server starting on http://0.0.0.0:5000")
    print(f"✓ API Documentation: http://localhost:5000/api/health")
    print("\nAvailable endpoints:")
    print("  GET  /api/grids")
    print("  GET  /api/grids/<id>")
    print("  GET  /api/alerts")
    print("  GET  /api/health")
    print("  GET  /api/analytics/occupancy")
    print("  POST /api/grids/<id>/command")
    print("\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)