#!/usr/bin/env python3
"""
DHSILED Database Models
MongoDB schemas and data access layer
"""

from pymongo import MongoClient, ASCENDING, DESCENDING
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import json

class DHSILEDDatabase:
    """Main database class for DHSILED system"""
    
    def __init__(self, connection_string="mongodb://localhost:27017/", db_name="dhsiled"):
        self.client = MongoClient(connection_string)
        self.db = self.client[db_name]
        
        # Collections
        self.grids = self.db.grids
        self.alerts = self.db.alerts
        self.health = self.db.health
        self.analytics = self.db.analytics
        self.events = self.db.events
        self.users = self.db.users
        
        self._create_indexes()
    
    def _create_indexes(self):
        """Create database indexes for performance"""
        # Grid collection indexes
        self.grids.create_index([("grid_id", ASCENDING)])
        self.grids.create_index([("timestamp", DESCENDING)])
        
        # Alerts collection indexes
        self.alerts.create_index([("alert_id", ASCENDING)], unique=True)
        self.alerts.create_index([("grid_id", ASCENDING)])
        self.alerts.create_index([("severity", ASCENDING)])
        self.alerts.create_index([("timestamp", DESCENDING)])
        self.alerts.create_index([("acknowledged", ASCENDING)])
        
        # Health collection indexes
        self.health.create_index([("grid_id", ASCENDING)])
        self.health.create_index([("timestamp", DESCENDING)])
        
        # Analytics collection indexes
        self.analytics.create_index([("timestamp", DESCENDING)])
        self.analytics.create_index([("type", ASCENDING)])
    
    ############################################################################
    # GRID STATUS OPERATIONS
    ############################################################################
    
    def save_grid_status(self, grid_data: Dict) -> bool:
        """Save grid status to database"""
        try:
            grid_data['saved_at'] = datetime.now(timezone.utc)
            self.grids.insert_one(grid_data)
            return True
        except Exception as e:
            print(f"Error saving grid status: {e}")
            return False
    
    def get_grid_current_status(self, grid_id: str) -> Optional[Dict]:
        """Get most recent status for a grid"""
        return self.grids.find_one(
            {"grid_id": grid_id},
            sort=[("timestamp", DESCENDING)]
        )
    
    def get_all_grids_current_status(self) -> List[Dict]:
        """Get current status of all grids"""
        pipeline = [
            {"$sort": {"timestamp": -1}},
            {"$group": {
                "_id": "$grid_id",
                "latest": {"$first": "$$ROOT"}
            }},
            {"$replaceRoot": {"newRoot": "$latest"}}
        ]
        return list(self.grids.aggregate(pipeline))
    
    def get_grid_history(self, grid_id: str, hours: int = 24) -> List[Dict]:
        """Get historical data for a grid"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        return list(self.grids.find(
            {
                "grid_id": grid_id,
                "timestamp": {"$gte": cutoff_time.isoformat()}
            },
            sort=[("timestamp", ASCENDING)]
        ))
    
    ############################################################################
    # ALERT OPERATIONS
    ############################################################################
    
    def save_alert(self, alert_data: Dict) -> bool:
        """Save alert to database"""
        try:
            alert_data['created_at'] = datetime.now(timezone.utc)
            alert_data['acknowledged'] = False
            alert_data['resolved'] = False
            self.alerts.insert_one(alert_data)
            return True
        except Exception as e:
            print(f"Error saving alert: {e}")
            return False
    
    def get_alert(self, alert_id: str) -> Optional[Dict]:
        """Get specific alert by ID"""
        return self.alerts.find_one({"alert_id": alert_id})
    
    def get_alerts(self, limit: int = 100, severity: str = None, 
                   acknowledged: bool = None) -> List[Dict]:
        """Get alerts with optional filters"""
        query = {}
        
        if severity:
            query['severity'] = severity
        
        if acknowledged is not None:
            query['acknowledged'] = acknowledged
        
        return list(self.alerts.find(
            query,
            sort=[("timestamp", DESCENDING)],
            limit=limit
        ))
    
    def acknowledge_alert(self, alert_id: str, user: str = "system") -> bool:
        """Mark alert as acknowledged"""
        result = self.alerts.update_one(
            {"alert_id": alert_id},
            {
                "$set": {
                    "acknowledged": True,
                    "acknowledged_at": datetime.now(timezone.utc),
                    "acknowledged_by": user
                }
            }
        )
        return result.modified_count > 0
    
    def resolve_alert(self, alert_id: str, resolution_notes: str = "") -> bool:
        """Mark alert as resolved"""
        result = self.alerts.update_one(
            {"alert_id": alert_id},
            {
                "$set": {
                    "resolved": True,
                    "resolved_at": datetime.now(timezone.utc),
                    "resolution_notes": resolution_notes
                }
            }
        )
        return result.modified_count > 0
    
    def get_active_alerts(self) -> List[Dict]:
        """Get all unresolved alerts"""
        return list(self.alerts.find(
            {"resolved": False},
            sort=[("severity", DESCENDING), ("timestamp", DESCENDING)]
        ))
    
    ############################################################################
    # HEALTH MONITORING OPERATIONS
    ############################################################################
    
    def save_health_data(self, health_data: Dict) -> bool:
        """Save device health data"""
        try:
            health_data['saved_at'] = datetime.now(timezone.utc)
            self.health.insert_one(health_data)
            return True
        except Exception as e:
            print(f"Error saving health data: {e}")
            return False
    
    def get_grid_health(self, grid_id: str) -> Optional[Dict]:
        """Get latest health data for a grid"""
        return self.health.find_one(
            {"grid_id": grid_id},
            sort=[("timestamp", DESCENDING)]
        )
    
    def get_all_grids_health(self) -> List[Dict]:
        """Get health status of all grids"""
        pipeline = [
            {"$sort": {"timestamp": -1}},
            {"$group": {
                "_id": "$grid_id",
                "latest": {"$first": "$$ROOT"}
            }},
            {"$replaceRoot": {"newRoot": "$latest"}}
        ]
        return list(self.health.aggregate(pipeline))
    
    def get_unhealthy_grids(self, health_score_threshold: float = 70.0) -> List[Dict]:
        """Get grids with health issues"""
        pipeline = [
            {"$sort": {"timestamp": -1}},
            {"$group": {
                "_id": "$grid_id",
                "latest": {"$first": "$$ROOT"}
            }},
            {"$replaceRoot": {"newRoot": "$latest"}},
            {"$match": {"health_score": {"$lt": health_score_threshold}}}
        ]
        return list(self.health.aggregate(pipeline))
    
    ############################################################################
    # ANALYTICS OPERATIONS
    ############################################################################
    
    def save_analytics(self, analytics_data: Dict) -> bool:
        """Save analytics snapshot"""
        try:
            analytics_data['timestamp'] = datetime.now(timezone.utc)
            self.analytics.insert_one(analytics_data)
            return True
        except Exception as e:
            print(f"Error saving analytics: {e}")
            return False
    
    def get_occupancy_trends(self, hours: int = 24) -> List[Dict]:
        """Get crowd occupancy trends"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        pipeline = [
            {"$match": {
                "timestamp": {"$gte": cutoff_time.isoformat()},
                "type": "occupancy"
            }},
            {"$sort": {"timestamp": ASCENDING}}
        ]
        
        return list(self.analytics.aggregate(pipeline))
    
    def get_density_heatmap(self) -> List[Dict]:
        """Get current density heatmap data"""
        current_states = self.get_all_grids_current_status()
        
        heatmap_data = []
        for grid in current_states:
            heatmap_data.append({
                'grid_id': grid.get('grid_id'),
                'people_count': grid.get('people_count', 0),
                'density': grid.get('crowd_density', {}).get('percentage', 0),
                'position': grid.get('position', {})
            })
        
        return heatmap_data
    
    ############################################################################
    # EVENT LOGGING
    ############################################################################
    
    def log_event(self, event_type: str, description: str, metadata: Dict = None) -> bool:
        """Log system event"""
        try:
            event = {
                'event_type': event_type,
                'description': description,
                'timestamp': datetime.now(timezone.utc),
                'metadata': metadata or {}
            }
            self.events.insert_one(event)
            return True
        except Exception as e:
            print(f"Error logging event: {e}")
            return False
    
    def get_events(self, limit: int = 100, event_type: str = None) -> List[Dict]:
        """Get system events"""
        query = {}
        if event_type:
            query['event_type'] = event_type
        
        return list(self.events.find(
            query,
            sort=[("timestamp", DESCENDING)],
            limit=limit
        ))
    
    ############################################################################
    # DATA CLEANUP
    ############################################################################
    
    def cleanup_old_data(self, days: int = 30) -> Dict:
        """Remove old data to free space"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_iso = cutoff_time.isoformat()
        
        results = {}
        
        results['grids'] = self.grids.delete_many(
            {"timestamp": {"$lt": cutoff_iso}}
        ).deleted_count
        
        results['health'] = self.health.delete_many(
            {"timestamp": {"$lt": cutoff_iso}}
        ).deleted_count
        
        results['alerts'] = self.alerts.delete_many({
            "timestamp": {"$lt": cutoff_iso},
            "resolved": True
        }).deleted_count
        
        results['analytics'] = self.analytics.delete_many(
            {"timestamp": {"$lt": cutoff_time}}
        ).deleted_count
        
        return results
    
    ############################################################################
    # DATABASE STATS
    ############################################################################
    
    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        stats = {
            'total_grids': self.grids.count_documents({}),
            'total_alerts': self.alerts.count_documents({}),
            'active_alerts': self.alerts.count_documents({"resolved": False}),
            'total_health_records': self.health.count_documents({}),
            'total_analytics': self.analytics.count_documents({}),
            'total_events': self.events.count_documents({}),
            'database_size': self.db.command("dbStats")['dataSize'],
            'last_updated': datetime.now(timezone.utc).isoformat()
        }
        
        return stats
    
    def close(self):
        """Close database connection"""
        self.client.close()


################################################################################
# EXAMPLE USAGE
################################################################################

if __name__ == "__main__":
    # Initialize database
    db = DHSILEDDatabase()
    
    print("DHSILED Database Manager")
    print("=" * 60)
    
    # Test database connection
    stats = db.get_database_stats()
    print(f"\nDatabase Statistics:")
    print(f"  Total Grid Records: {stats['total_grids']}")
    print(f"  Total Alerts: {stats['total_alerts']}")
    print(f"  Active Alerts: {stats['active_alerts']}")
    print(f"  Health Records: {stats['total_health_records']}")
    print(f"  Database Size: {stats['database_size']} bytes")
    
    # Example: Save test data
    test_grid_data = {
        'grid_id': 'G01',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'people_count': 45,
        'crowd_density': {'level': 'normal', 'percentage': 30}
    }
    
    if db.save_grid_status(test_grid_data):
        print("\n✓ Test grid status saved")
    
    # Example: Get current status
    current = db.get_grid_current_status('G01')
    if current:
        print(f"✓ Current G01 status: {current['people_count']} people")
    
    db.close()
    print("\nDatabase connection closed.")