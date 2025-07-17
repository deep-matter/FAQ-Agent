import psycopg2
from app.database.connection import db_connection
import logging

logger = logging.getLogger(__name__)

def initialize_database():
    """Initialize database tables"""
    
    sessions_table = """
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
    """
    
    user_contexts_table = """
        CREATE TABLE IF NOT EXISTS user_contexts (
            user_id VARCHAR(255) PRIMARY KEY,
            preferences JSONB,
            interaction_count INTEGER DEFAULT 0,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """
    
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_session_id ON sessions(session_id);",
        "CREATE INDEX IF NOT EXISTS idx_user_id ON sessions(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_timestamp ON sessions(timestamp);"
    ]
    
    try:
        conn = db_connection.get_connection()
        cur = conn.cursor()
        
        cur.execute(sessions_table)
        cur.execute(user_contexts_table)
        
        for index in indexes:
            cur.execute(index)
        
        conn.commit()
        cur.close()
        conn.close()
        
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise