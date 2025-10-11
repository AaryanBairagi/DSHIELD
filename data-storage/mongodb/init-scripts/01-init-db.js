// DHSILED MongoDB Initialization Script
// Creates database, collections, and indexes

print('========================================');
print('DHSILED MongoDB Initialization');
print('========================================');

// Switch to dhsiled database
db = db.getSiblingDB('dhsiled');

// Create collections
print('\n📁 Creating collections...');

db.createCollection('grids');
db.createCollection('alerts');
db.createCollection('health');
db.createCollection('analytics');
db.createCollection('events');
db.createCollection('users');

print('✓ Collections created');

// Create indexes for grids collection
print('\n🔍 Creating indexes for grids collection...');

db.grids.createIndex({ "grid_id": 1 });
db.grids.createIndex({ "timestamp": -1 });
db.grids.createIndex({ "grid_id": 1, "timestamp": -1 });
db.grids.createIndex({ "crowd_density.level": 1 });

print('✓ Grids indexes created');

// Create indexes for alerts collection
print('\n🔍 Creating indexes for alerts collection...');

db.alerts.createIndex({ "id": 1 }, { unique: true });
db.alerts.createIndex({ "grid_id": 1 });
db.alerts.createIndex({ "severity": 1 });
db.alerts.createIndex({ "timestamp": -1 });
db.alerts.createIndex({ "acknowledged": 1 });
db.alerts.createIndex({ "resolved": 1 });
db.alerts.createIndex({ "grid_id": 1, "timestamp": -1 });

print('✓ Alerts indexes created');

// Create indexes for health collection
print('\n🔍 Creating indexes for health collection...');

db.health.createIndex({ "grid_id": 1 });
db.health.createIndex({ "timestamp": -1 });
db.health.createIndex({ "health_score": 1 });
db.health.createIndex({ "grid_id": 1, "timestamp": -1 });

print('✓ Health indexes created');

// Create indexes for analytics collection
print('\n🔍 Creating indexes for analytics collection...');

db.analytics.createIndex({ "timestamp": -1 });
db.analytics.createIndex({ "type": 1 });
db.analytics.createIndex({ "type": 1, "timestamp": -1 });

print('✓ Analytics indexes created');

// Create indexes for events collection
print('\n🔍 Creating indexes for events collection...');

db.events.createIndex({ "timestamp": -1 });
db.events.createIndex({ "event_type": 1 });
db.events.createIndex({ "event_type": 1, "timestamp": -1 });

print('✓ Events indexes created');

// Create indexes for users collection
print('\n🔍 Creating indexes for users collection...');

db.users.createIndex({ "username": 1 }, { unique: true });
db.users.createIndex({ "email": 1 }, { unique: true });

print('✓ Users indexes created');

// Insert initial data
print('\n📝 Inserting initial data...');

// Insert default admin user
db.users.insertOne({
    username: 'admin',
    email: 'admin@dhsiled.com',
    password: '$2b$10$XO0qXqXqXqXqXqXqXqXqXeO', // Hashed password
    role: 'admin',
    created_at: new Date(),
    last_login: null
});

print('✓ Initial data inserted');

// Create TTL index for automatic data cleanup
print('\n⏰ Creating TTL indexes for automatic cleanup...');

// Auto-delete grid data older than 30 days
db.grids.createIndex(
    { "timestamp": 1 },
    { expireAfterSeconds: 2592000 } // 30 days
);

// Auto-delete resolved alerts older than 90 days
db.alerts.createIndex(
    { "resolved_at": 1 },
    { expireAfterSeconds: 7776000, partialFilterExpression: { "resolved": true } } // 90 days
);

// Auto-delete health data older than 30 days
db.health.createIndex(
    { "timestamp": 1 },
    { expireAfterSeconds: 2592000 } // 30 days
);

print('✓ TTL indexes created');

print('\n========================================');
print('✓ Database initialization complete!');
print('========================================');