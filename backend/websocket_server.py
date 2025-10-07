#!/usr/bin/env python3
"""
DHSILED WebSocket Server
Bridges MQTT messages to WebSocket for real-time dashboard updates
"""

import asyncio
import json
import websockets
import paho.mqtt.client as mqtt
from datetime import datetime

# Connected WebSocket clients
connected_clients = set()

def on_mqtt_message(client, userdata, message):
    """Forward MQTT messages to WebSocket clients"""
    try:
        payload = message.payload.decode()
        data = json.loads(payload)
        
        # Add message type based on topic
        if 'status' in message.topic:
            data['type'] = 'grid_status'
        elif 'alerts' in message.topic:
            data['type'] = 'alert'
        elif 'health' in message.topic:
            data['type'] = 'health'
        else:
            data['type'] = 'system'
        
        # Broadcast to all WebSocket clients
        asyncio.create_task(broadcast_message(json.dumps(data)))
        
    except Exception as e:
        print(f"Error processing MQTT message: {e}")

async def broadcast_message(message):
    """Broadcast message to all connected WebSocket clients"""
    if connected_clients:
        await asyncio.gather(
            *[client.send(message) for client in connected_clients],
            return_exceptions=True
        )

async def websocket_handler(websocket, path):
    """Handle WebSocket connections"""
    connected_clients.add(websocket)
    print(f"✓ Client connected. Total clients: {len(connected_clients)}")
    
    try:
        async for message in websocket:
            # Handle incoming messages from dashboard if needed
            try:
                data = json.loads(message)
                print(f"Received from client: {data}")
            except:
                pass
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected_clients.remove(websocket)
        print(f"✗ Client disconnected. Total clients: {len(connected_clients)}")

def start_mqtt_client():
    """Start MQTT client to subscribe to grid updates"""
    client = mqtt.Client(client_id="dhsiled_websocket_bridge")
    client.on_message = on_mqtt_message
    
    try:
        client.connect("localhost", 1883, 60)
        client.subscribe("dhsiled/#")  # Subscribe to all DHSILED topics
        client.loop_start()
        print("✓ MQTT client connected and subscribed to dhsiled/#")
        return client
    except Exception as e:
        print(f"✗ MQTT connection failed: {e}")
        print("  Make sure Mosquitto MQTT broker is running:")
        print("  sudo systemctl start mosquitto")
        return None

async def main():
    print("="*60)
    print("DHSILED WebSocket Server Starting...")
    print("="*60)
    
    # Start MQTT client
    mqtt_client = start_mqtt_client()
    if not mqtt_client:
        print("\n⚠️  Starting without MQTT connection")
        print("   WebSocket will work but no real-time data")
    
    # Start WebSocket server
    async with websockets.serve(websocket_handler, "0.0.0.0", 8080):
        print(f"\n✓ WebSocket server running on ws://0.0.0.0:8080")
        print(f"✓ Dashboard can connect to ws://localhost:8080")
        print("\nWaiting for connections...\n")
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nShutting down gracefully...")