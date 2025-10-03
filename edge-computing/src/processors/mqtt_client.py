# edge-computing/src/processors/mqtt_client.py
"""
MQTT Client for DHSILED Edge Devices
Handles communication between edge nodes and central system
"""

import asyncio
import json
import time
import ssl
from datetime import datetime, timezone
from typing import Dict, Callable, Optional, Any
import logging

try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    print("Warning: paho-mqtt not available, using mock implementation")

class MQTTClient:
    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.client = None
        self.connected = False
        self.message_handler = None
        
        # MQTT Configuration
        mqtt_config = config.get('mqtt', {})
        self.broker_host = mqtt_config.get('host', 'localhost')
        self.broker_port = mqtt_config.get('port', 1883)
        self.username = mqtt_config.get('username')
        self.password = mqtt_config.get('password')
        self.use_ssl = mqtt_config.get('ssl', False)
        self.keepalive = mqtt_config.get('keepalive', 60)
        self.qos = mqtt_config.get('qos', 1)
        
        # Topic configuration
        self.grid_id = config.get('grid.id', 'G01')
        self.base_topic = f"dhsiled/grids/{self.grid_id}"
        
        # Message queuing for offline scenarios
        self.message_queue = []
        self.max_queue_size = 1000
        
        # Statistics
        self.stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'connection_attempts': 0,
            'last_connected': None,
            'total_uptime': 0
        }
        
    async def connect(self):
        """Connect to MQTT broker"""
        try:
            if not MQTT_AVAILABLE:
                self.client = MockMQTTClient()
                await self.client.connect()
                self.connected = True
                self.logger.info("Connected to mock MQTT broker")
                return
            
            self.client = mqtt.Client(client_id=f"dhsiled_edge_{self.grid_id}_{int(time.time())}")
            
            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect
            self.client.on_message = self._on_message
            self.client.on_publish = self._on_publish
            self.client.on_subscribe = self._on_subscribe
            
            # Configure credentials
            if self.username and self.password:
                self.client.username_pw_set(self.username, self.password)
            
            # Configure SSL if needed
            if self.use_ssl:
                context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
                self.client.tls_set_context(context)
            
            # Set will message for ungraceful disconnections
            will_topic = f"{self.base_topic}/status"
            will_payload = json.dumps({
                'grid_id': self.grid_id,
                'status': 'offline',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            self.client.will_set(will_topic, will_payload, qos=1, retain=True)
            
            self.logger.info(f"Connecting to MQTT broker at {self.broker_host}:{self.broker_port}")
            
            # Connect to broker
            self.stats['connection_attempts'] += 1
            await asyncio.to_thread(
                self.client.connect, 
                self.broker_host, 
                self.broker_port, 
                self.keepalive
            )
            
        except Exception as e:
            self.logger.error(f"MQTT connection failed: {e}")
            raise
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for successful connection"""
        if rc == 0:
            self.connected = True
            self.stats['last_connected'] = datetime.now(timezone.utc)
            self.logger.info(f"MQTT connected successfully (Grid {self.grid_id})")
            
            # Subscribe to command topics
            command_topics = [
                f"{self.base_topic}/commands",
                f"dhsiled/system/commands",
                f"dhsiled/system/broadcast"
            ]
            
            for topic in command_topics:
                client.subscribe(topic, qos=self.qos)
                self.logger.debug(f"Subscribed to topic: {topic}")
            
            # Send online status
            online_message = {
                'grid_id': self.grid_id,
                'status': 'online',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'version': '1.0.0'
            }
            client.publish(f"{self.base_topic}/status", json.dumps(online_message), qos=1, retain=True)
            
            # Send any queued messages
            asyncio.create_task(self._process_message_queue())
            
        else:
            self.logger.error(f"MQTT connection failed with code {rc}")
            self.connected = False
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback for disconnection"""
        self.connected = False
        if rc == 0:
            self.logger.info("MQTT disconnected gracefully")
        else:
            self.logger.warning(f"MQTT disconnected unexpectedly (code {rc})")
    
    def _on_message(self, client, userdata, message):
        """Callback for received messages"""
        try:
            self.stats['messages_received'] += 1
            topic = message.topic
            payload = message.payload
            
            self.logger.debug(f"Received message on topic {topic}")
            
            if self.message_handler:
                asyncio.create_task(self.message_handler(topic, payload))
                
        except Exception as e:
            self.logger.error(f"Error processing received message: {e}")
    
    def _on_publish(self, client, userdata, mid):
        """Callback for successful message publish"""
        self.stats['messages_sent'] += 1
        self.logger.debug(f"Message published successfully (mid: {mid})")
    
    def _on_subscribe(self, client, userdata, mid, granted_qos):
        """Callback for successful subscription"""
        self.logger.debug(f"Subscription confirmed (mid: {mid}, QoS: {granted_qos})")
    
    async def publish(self, topic: str, payload: str, qos: Optional[int] = None, retain: bool = False):
        """Publish message to MQTT broker"""
        try:
            if qos is None:
                qos = self.qos
            
            if self.connected and self.client:
                # Publish directly
                result = self.client.publish(topic, payload, qos=qos, retain=retain)
                
                if result.rc != mqtt.MQTT_ERR_SUCCESS:
                    self.logger.warning(f"Publish failed for topic {topic}: {result.rc}")
                    await self._queue_message(topic, payload, qos, retain)
                
        except Exception as e:
            self.logger.error(f"Error publishing message: {e}")
            await self._queue_message(topic, payload, qos, retain)
    
    async def _queue_message(self, topic: str, payload: str, qos: int, retain: bool):
        """Queue message for later delivery"""
        if len(self.message_queue) >= self.max_queue_size:
            # Remove oldest message
            removed = self.message_queue.pop(0)
            self.logger.warning(f"Message queue full, removed oldest message for topic {removed['topic']}")
        
        message = {
            'topic': topic,
            'payload': payload,
            'qos': qos,
            'retain': retain,
            'timestamp': time.time()
        }
        
        self.message_queue.append(message)
        self.logger.debug(f"Queued message for topic {topic}")
    
    async def _process_message_queue(self):
        """Process queued messages when connection is restored"""
        if not self.message_queue:
            return
        
        self.logger.info(f"Processing {len(self.message_queue)} queued messages")
        
        messages_to_process = self.message_queue.copy()
        self.message_queue.clear()
        
        for message in messages_to_process:
            try:
                # Check if message is not too old (5 minutes max)
                if time.time() - message['timestamp'] < 300:
                    await self.publish(
                        message['topic'],
                        message['payload'],
                        message['qos'],
                        message['retain']
                    )
                    await asyncio.sleep(0.1)  # Small delay between messages
                else:
                    self.logger.debug(f"Discarded old queued message for topic {message['topic']}")
                    
            except Exception as e:
                self.logger.error(f"Error processing queued message: {e}")
        
        self.logger.info("Finished processing message queue")
    
    def set_message_handler(self, handler: Callable[[str, bytes], None]):
        """Set callback function for handling received messages"""
        self.message_handler = handler
    
    async def run(self):
        """Main MQTT client loop"""
        while True:
            try:
                if not self.connected and MQTT_AVAILABLE:
                    self.logger.info("Attempting to reconnect to MQTT broker...")
                    await self.connect()
                
                if self.client and hasattr(self.client, 'loop'):
                    # Process MQTT network traffic
                    self.client.loop(timeout=1.0)
                
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"MQTT client loop error: {e}")
                await asyncio.sleep(5)  # Wait before retry
    
    async def disconnect(self):
        """Gracefully disconnect from MQTT broker"""
        try:
            if self.connected and self.client:
                # Send offline status
                offline_message = {
                    'grid_id': self.grid_id,
                    'status': 'offline',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                self.client.publish(
                    f"{self.base_topic}/status", 
                    json.dumps(offline_message), 
                    qos=1, 
                    retain=True
                )
                
                # Wait a moment for message to be sent
                await asyncio.sleep(1)
                
                # Disconnect
                self.client.disconnect()
                
            self.connected = False
            self.logger.info("MQTT client disconnected")
            
        except Exception as e:
            self.logger.error(f"Error during MQTT disconnect: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get MQTT client statistics"""
        stats = self.stats.copy()
        stats.update({
            'connected': self.connected,
            'queued_messages': len(self.message_queue),
            'broker_host': self.broker_host,
            'broker_port': self.broker_port
        })
        
        if self.stats['last_connected']:
            uptime = (datetime.now(timezone.utc) - self.stats['last_connected']).total_seconds()
            stats['current_session_uptime'] = uptime
        
        return stats


class MockMQTTClient:
    """Mock MQTT client for testing and development"""
    
    def __init__(self):
        self.connected = False
        self.message_handler = None
        self.published_messages = []
    
    async def connect(self):
        """Mock connection"""
        await asyncio.sleep(0.1)  # Simulate connection time
        self.connected = True
        print("Mock MQTT: Connected to broker")
    
    def publish(self, topic: str, payload: str, qos: int = 0, retain: bool = False):
        """Mock publish"""
        message = {
            'topic': topic,
            'payload': payload,
            'qos': qos,
            'retain': retain,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        self.published_messages.append(message)
        print(f"Mock MQTT: Published to {topic}")
        
        # Return mock result
        class MockResult:
            rc = 0  # Success
        
        return MockResult()
    
    def subscribe(self, topic: str, qos: int = 0):
        """Mock subscribe"""
        print(f"Mock MQTT: Subscribed to {topic}")
    
    def disconnect(self):
        """Mock disconnect"""
        self.connected = False
        print("Mock MQTT: Disconnected")
    
    def loop(self, timeout: float = 1.0):
        """Mock network loop"""
        pass  # No-op for mock
    
    def get_published_messages(self):
        """Get all published messages (for testing)"""
        return self.published_messages.copy()
    
    def clear_published_messages(self):
        """Clear published message history"""
        self.published_messages.clear()