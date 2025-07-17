from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class FAQQueryRequest(BaseModel):
    """Request model for FAQ queries"""
    query: str = Field(..., min_length=1, max_length=500, description="User's FAQ question")
    session_id: Optional[str] = Field(None, description="Session identifier for conversation continuity")
    user_id: Optional[str] = Field(None, description="User identifier for personalization")

class FAQQueryResponse(BaseModel):
    """Response model for FAQ queries"""
    answer: str = Field(..., description="Generated FAQ response")
    confidence: str = Field(..., description="Response confidence level")
    sources: List[str] = Field(default_factory=list, description="Source attribution")
    session_id: str = Field(..., description="Session identifier")
    timestamp: datetime = Field(..., description="Response timestamp")
    intent: Optional[str] = Field(None, description="Detected query intent")

class SessionHistoryResponse(BaseModel):
    """Response model for session history"""
    session_id: str
    history: List[dict]
    total_interactions: int

class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    service: str
    version: str
    timestamp: str

class SystemStatusResponse(BaseModel):
    """System status response model"""
    database: str
    vector_store: str
    agents: str

class UserStatsResponse(BaseModel):
    """User statistics response model"""
    user_id: str
    preferences: Optional[dict]
    interaction_count: int
    last_active: datetime
    created_at: datetime

class ErrorResponse(BaseModel):
    """Error response model"""
    error: str
    message: str
    timestamp: datetime