CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    user_id VARCHAR(255),
    query TEXT NOT NULL,
    response TEXT NOT NULL,
    confidence VARCHAR(50),
    intent VARCHAR(100),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

CREATE TABLE IF NOT EXISTS user_contexts (
    user_id VARCHAR(255) PRIMARY KEY,
    preferences JSONB,
    interaction_count INTEGER DEFAULT 0,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_session_id ON sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_timestamp ON sessions(timestamp);