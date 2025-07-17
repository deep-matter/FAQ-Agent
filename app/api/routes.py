from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.security import HTTPBearer
import asyncio
from app.api.models import (
    FAQQueryRequest, 
    FAQQueryResponse, 
    SessionHistoryResponse,
    HealthResponse,
    SystemStatusResponse,
    UserStatsResponse,
    ErrorResponse
)
from app.workflow.orchestrator import FAQWorkflowOrchestrator
from app.core.session_manager import SessionManager
from app.database.connection import db_connection
from app.config.settings import settings
from datetime import datetime
import uuid
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter()

# Security
security = HTTPBearer(auto_error=False)

# Global instances
workflow_orchestrator = None
session_manager = None

def get_workflow_orchestrator():
    """Dependency to get workflow orchestrator"""
    global workflow_orchestrator
    if not workflow_orchestrator:
        workflow_orchestrator = FAQWorkflowOrchestrator()
    return workflow_orchestrator

def get_session_manager():
    """Dependency to get session manager"""
    global session_manager
    if not session_manager:
        session_manager = SessionManager()
    return session_manager

def sanitize_input(text: str) -> str:
    """Enhanced input sanitization"""
    if not text:
        return ""
    
    # Remove control characters and potential XSS
    sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
    
    # Remove HTML tags and script content
    sanitized = re.sub(r'<[^>]*>', '', sanitized)
    
    # Remove potential SQL injection patterns
    dangerous_patterns = [
        r'union\s+select', r'drop\s+table', r'delete\s+from',
        r'insert\s+into', r'update\s+set', r'exec\s*\(',
        r'xp_cmdshell', r'sp_executesql'
    ]
    
    for pattern in dangerous_patterns:
        sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
    
    return sanitized.strip()

def validate_query_length(query: str) -> bool:
    """Validate query length constraints"""
    return 1 <= len(query.strip()) <= 500

def validate_session_id(session_id: str) -> bool:
    """Validate session ID format"""
    if not session_id:
        return False
    
    # UUID format validation
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
    return re.match(uuid_pattern, session_id, re.IGNORECASE) is not None

async def verify_api_health() -> bool:
    """Verify API components are healthy"""
    try:
        # Test database connection
        if not db_connection.test_connection():
            return False
        
        # Test workflow orchestrator
        orchestrator = get_workflow_orchestrator()
        if not orchestrator or not orchestrator.workflow_app:
            return False
        
        return True
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return False

@router.post("/faq/query", response_model=FAQQueryResponse)
async def process_faq_query(
    request: Request,
    faq_request: FAQQueryRequest,
    orchestrator: FAQWorkflowOrchestrator = Depends(get_workflow_orchestrator),
    session_mgr: SessionManager = Depends(get_session_manager)
):
    """Process user query through FAQ AGENTIC FLOW system with security"""
    start_time = datetime.now()
    
    try:
        # Input validation
        clean_query = sanitize_input(faq_request.query)
        
        if not validate_query_length(clean_query):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query must be between 1 and 500 characters"
            )
        
        # Session ID validation
        session_id = faq_request.session_id or str(uuid.uuid4())
        if faq_request.session_id and not validate_session_id(faq_request.session_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid session ID format"
            )
        
        logger.info(
            f"Processing FAQ query: {clean_query[:50]}... "
            f"(Session: {session_id}, User: {faq_request.user_id})"
        )
        
        # Process through agent workflow with timeout
        try:
            result = await asyncio.wait_for(
                orchestrator.process_query(clean_query, session_id),
                timeout=30.0  # 30 second timeout
            )
        except asyncio.TimeoutError:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Request timed out. Please try again."
            )
        
        if not result or not result.get("response"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate response"
            )
        
        # Save interaction to session
        try:
            session_mgr.save_interaction(
                session_id=session_id,
                user_id=faq_request.user_id or "anonymous",
                query=clean_query,
                response=result["response"],
                confidence=result.get("confidence", "unknown"),
                intent=result.get("intent"),
                metadata={
                    "keywords": result.get("keywords"),
                    "processing_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
                    "ip_address": request.client.host if request.client else "unknown"
                }
            )
        except Exception as e:
            logger.error(f"Failed to save interaction: {e}")
            # Don't fail the request if session save fails
        
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Query processed in {processing_time:.2f}s")
        
        sources = result.get("sources", [])
        if isinstance(sources, str):
            sources = [sources] if sources else []
        elif not isinstance(sources, list):
            sources = []
        
        return FAQQueryResponse(
            answer=result["response"],
            confidence=result.get("confidence", "unknown"),
            sources=sources,
            session_id=session_id,
            timestamp=datetime.now(),
            intent=result.get("intent")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"FAQ query processing failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get("/faq/session/{session_id}/history", response_model=SessionHistoryResponse)
async def get_session_history(
    request: Request,
    session_id: str,
    limit: int = 10,
    session_mgr: SessionManager = Depends(get_session_manager)
):
    """Retrieve conversation history for a session"""
    try:
        if not validate_session_id(session_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid session ID format"
            )
        
        if not (1 <= limit <= 50):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Limit must be between 1 and 50"
            )
        
        history = session_mgr.get_session_context(session_id, limit)
        
        return SessionHistoryResponse(
            session_id=session_id,
            history=history,
            total_interactions=len(history)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve session history: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session history"
        )

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """API health status with comprehensive checks"""
    try:
        is_healthy = await verify_api_health()
        
        return HealthResponse(
            status="healthy" if is_healthy else "degraded",
            service="FAQ AGENTIC FLOW API",
            version="1.0.0",
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            service="FAQ AGENTIC FLOW API",
            version="1.0.0",
            timestamp=datetime.now().isoformat()
        )

@router.get("/status", response_model=SystemStatusResponse)
async def system_status(request: Request):
    """Check system component status with detailed diagnostics"""
    status_result = SystemStatusResponse(
        database="unknown",
        vector_store="unknown",
        agents="unknown"
    )
    
    try:
        # Check database connectivity
        if db_connection.test_connection():
            status_result.database = "healthy"
        else:
            status_result.database = "unhealthy"
    except Exception as e:
        logger.error(f"Database status check failed: {e}")
        status_result.database = "unhealthy"
    
    try:
        # Check agent system
        orchestrator = get_workflow_orchestrator()
        if orchestrator and orchestrator.workflow_app:
            status_result.agents = "healthy"
            status_result.vector_store = "healthy"
        else:
            status_result.agents = "unhealthy"
            status_result.vector_store = "unhealthy"
    except Exception as e:
        logger.error(f"Agent system status check failed: {e}")
        status_result.agents = "unhealthy"
        status_result.vector_store = "unhealthy"
    
    return status_result

@router.get("/users/{user_id}/stats", response_model=UserStatsResponse)
async def get_user_statistics(
    request: Request,
    user_id: str,
    session_mgr: SessionManager = Depends(get_session_manager)
):
    """Get user interaction statistics with input validation"""
    try:
        # Validate user ID
        sanitized_user_id = sanitize_input(user_id)
        if not sanitized_user_id or len(sanitized_user_id) > 255:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID"
            )
        
        stats = session_mgr.get_user_stats(sanitized_user_id)
        
        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return UserStatsResponse(**stats)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve user stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user statistics"
        )