import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import json
import uuid
from contextlib import contextmanager
from app.database.connection import db_connection
import logging

logger = logging.getLogger(__name__)

class SessionManager:
    """PostgreSQL-based session management for stateful conversations"""
    
    def __init__(self):
        self.cache = {}
        self.cache_max_size = 1000
    
    @contextmanager
    def get_db_connection(self):
        """Context manager for database connections to prevent leaks"""
        conn = None
        try:
            conn = db_connection.get_connection()
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def get_session_context(self, session_id: str, limit: int = 5) -> list:
        """Retrieve conversation history for contextual responses"""
        cache_key = f"session_{session_id}"
        if cache_key in self.cache:
            return self.cache[cache_key][-limit:]
        
        try:
            with self.get_db_connection() as conn:
                cur = db_connection.get_cursor(conn)
                
                cur.execute("""
                    SELECT query, response, confidence, intent, metadata, timestamp
                    FROM sessions
                    WHERE session_id = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                """, (session_id, limit))
                
                history = cur.fetchall()
                cur.close()
            
            formatted_history = [
                {
                    "query": record["query"],
                    "response": record["response"],
                    "confidence": record["confidence"],
                    "intent": record["intent"],
                    "metadata": record["metadata"],
                    "timestamp": record["timestamp"]
                }
                for record in history
            ]
            
            self._update_cache(cache_key, formatted_history)
            return formatted_history
            
        except Exception as e:
            logger.error(f"Error retrieving session context: {e}")
            return []
    
    def save_interaction(self, session_id: str, user_id: str, query: str, 
                        response: str, confidence: str, intent: str | None = None, 
                        metadata: dict | None = None) -> None:
        """Save interaction to database for session persistence"""
        try:
            with self.get_db_connection() as conn:
                cur = conn.cursor()
                
                cur.execute("""
                    INSERT INTO sessions (session_id, user_id, query, response, confidence, intent, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    session_id, 
                    user_id, 
                    query, 
                    response, 
                    confidence, 
                    intent, 
                    json.dumps(metadata or {})
                ))
                
                conn.commit()
                cur.close()
            
            cache_key = f"session_{session_id}"
            if cache_key not in self.cache:
                self.cache[cache_key] = []
            
            self.cache[cache_key].append({
                "query": query,
                "response": response,
                "confidence": confidence,
                "intent": intent,
                "metadata": metadata,
                "timestamp": datetime.now()
            })
            
            self._update_user_context(user_id)
            
        except Exception as e:
            logger.error(f"Error saving interaction: {e}")
            raise
    
    def _update_user_context(self, user_id: str) -> None:
        """Update user interaction statistics"""
        if not user_id:
            return
        
        try:
            with self.get_db_connection() as conn:
                cur = conn.cursor()
                
                cur.execute("""
                    INSERT INTO user_contexts (user_id, interaction_count, last_active)
                    VALUES (%s, 1, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id)
                    DO UPDATE SET 
                        interaction_count = user_contexts.interaction_count + 1,
                        last_active = CURRENT_TIMESTAMP
                """, (user_id,))
                
                conn.commit()
                cur.close()
                
        except Exception as e:
            logger.error(f"Error updating user context: {e}")
    
    def cleanup_old_sessions(self, days: int = 30) -> int:
        """Clean up old sessions to maintain performance"""
        try:
            with self.get_db_connection() as conn:
                cur = conn.cursor()
                
                cur.execute("""
                    DELETE FROM sessions
                    WHERE timestamp < CURRENT_TIMESTAMP - INTERVAL '%s days'
                """, (days,))
                
                deleted_count = cur.rowcount
                conn.commit()
                cur.close()
            
            self._clear_cache()
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {e}")
            return 0
    
    def get_user_stats(self, user_id: str) -> dict | None:
        """Get user interaction statistics"""
        try:
            with self.get_db_connection() as conn:
                cur = db_connection.get_cursor(conn)
                
                cur.execute("""
                    SELECT * FROM user_contexts WHERE user_id = %s
                """, (user_id,))
                
                stats = cur.fetchone()
                cur.close()
            
            return dict(stats) if stats else None
            
        except Exception as e:
            logger.error(f"Error retrieving user stats: {e}")
            return None
    
    def _update_cache(self, cache_key: str, data: list) -> None:
        """Update cache with size limit management"""
        if len(self.cache) >= self.cache_max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        self.cache[cache_key] = data
    
    def _clear_cache(self) -> None:
        """Clear all cached data"""
        self.cache.clear()
    
    def get_session_stats(self, session_id: str) -> dict:
        """Get statistics for a specific session"""
        try:
            with self.get_db_connection() as conn:
                cur = conn.cursor()
                
                cur.execute("""
                    SELECT 
                        COUNT(*) as total_interactions,
                        MIN(timestamp) as first_interaction,
                        MAX(timestamp) as last_interaction,
                        AVG(CASE WHEN confidence = 'high' THEN 1 ELSE 0 END) as high_confidence_ratio
                    FROM sessions 
                    WHERE session_id = %s
                """, (session_id,))
                
                stats = cur.fetchone()
                cur.close()
                
                return {
                    "session_id": session_id,
                    "total_interactions": stats[0] if stats else 0,
                    "first_interaction": stats[1] if stats else None,
                    "last_interaction": stats[2] if stats else None,
                    "high_confidence_ratio": float(stats[3]) if stats and stats[3] else 0.0
                }
                
        except Exception as e:
            logger.error(f"Error retrieving session stats: {e}")
            return {
                "session_id": session_id,
                "total_interactions": 0,
                "first_interaction": None,
                "last_interaction": None,
                "high_confidence_ratio": 0.0
            }