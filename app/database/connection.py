import psycopg2
from psycopg2.extras import RealDictCursor
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

class DatabaseConnection:
    """Database connection manager"""
    
    def __init__(self):
        self.config = settings.db_config
    
    def get_connection(self):
        """Get database connection"""
        try:
            conn = psycopg2.connect(**self.config)
            return conn
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def get_cursor(self, connection=None):
        """Get database cursor"""
        if connection is None:
            connection = self.get_connection()
        return connection.cursor(cursor_factory=RealDictCursor)
    
    def test_connection(self):
        """Test database connectivity"""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Database test failed: {e}")
            return False

db_connection = DatabaseConnection()