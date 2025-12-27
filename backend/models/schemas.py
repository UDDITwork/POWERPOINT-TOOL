"""
Pydantic Models for API Request/Response Validation

Author: AI Patent Diagram Generator
License: MIT
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime


class JobStatus(str, Enum):
    """Enum for job status states."""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DiagramCreateRequest(BaseModel):
    """Request model for creating a new diagram."""
    prompt: str = Field(
        ...,
        min_length=10,
        max_length=5000,
        description="Natural language description of the desired diagram"
    )
    session_id: Optional[str] = Field(
        None,
        description="Optional session ID to track related diagrams"
    )
    options: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional generation parameters"
    )

    @validator('prompt')
    def prompt_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Prompt cannot be empty')
        return v.strip()

    class Config:
        schema_extra = {
            "example": {
                "prompt": "Create a flowchart with 3 steps: input (100), processing (200), output (300)",
                "session_id": "session-abc123",
                "options": {
                    "slide_width": 10.0,
                    "slide_height": 7.5
                }
            }
        }


class DiagramRefineRequest(BaseModel):
    """Request model for refining an existing diagram."""
    session_id: str = Field(
        ...,
        description="Session ID of the diagram to refine"
    )
    refinement_prompt: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="Description of changes to make"
    )

    @validator('refinement_prompt')
    def refinement_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Refinement prompt cannot be empty')
        return v.strip()

    class Config:
        schema_extra = {
            "example": {
                "session_id": "session-abc123",
                "refinement_prompt": "Make the processing block wider and add a label"
            }
        }


class DiagramStatusResponse(BaseModel):
    """Response model for diagram job status."""
    job_id: str
    session_id: Optional[str] = None
    status: JobStatus
    message: str = ""
    progress: int = Field(0, ge=0, le=100, description="Progress percentage (0-100)")
    download_url: Optional[str] = None
    preview_url: Optional[str] = None
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        schema_extra = {
            "example": {
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "session_id": "session-abc123",
                "status": "completed",
                "message": "Diagram ready for download",
                "progress": 100,
                "download_url": "/api/diagram/download/550e8400-e29b-41d4-a716-446655440000.pptx",
                "preview_url": "/api/diagram/preview/550e8400-e29b-41d4-a716-446655440000.png"
            }
        }


class DiagramMetadata(BaseModel):
    """Metadata for a generated diagram."""
    title: Optional[str] = None
    author: Optional[str] = None
    diagram_type: Optional[str] = None
    element_count: int = 0
    connector_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SessionInfo(BaseModel):
    """Information about a user session."""
    session_id: str
    created_at: datetime
    last_activity: datetime
    total_diagrams: int = 0
    context: Optional[Dict[str, Any]] = None


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        schema_extra = {
            "example": {
                "error": "AI service not configured",
                "detail": "ANTHROPIC_API_KEY environment variable not set",
                "timestamp": "2025-12-27T10:30:00Z"
            }
        }
