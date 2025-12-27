"""
FastAPI Backend for AI Patent Diagram Generator

Main application entry point with REST API endpoints.

Author: AI Patent Diagram Generator
License: MIT
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import os
import uuid
import logging
from pathlib import Path
from datetime import datetime

# Import our modules
from ai.claude_agent import ClaudeDiagramAgent
from diagram_engine.pptx_generator import PPTXDiagramGenerator
from models.schemas import (
    DiagramCreateRequest,
    DiagramRefineRequest,
    DiagramStatusResponse,
    JobStatus
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="AI Patent Diagram Generator",
    description="Generate fully editable PowerPoint diagrams using AI",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS Configuration
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage configuration
STORAGE_PATH = Path(os.getenv("STORAGE_PATH", "./generated_diagrams"))
STORAGE_PATH.mkdir(parents=True, exist_ok=True)

PREVIEW_PATH = STORAGE_PATH / "previews"
PREVIEW_PATH.mkdir(parents=True, exist_ok=True)

# Initialize AI agent
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not ANTHROPIC_API_KEY:
    logger.warning("ANTHROPIC_API_KEY not set! AI features will not work.")
    claude_agent = None
else:
    claude_agent = ClaudeDiagramAgent(
        api_key=ANTHROPIC_API_KEY,
        model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5")
    )

# In-memory job tracking (use Redis in production)
job_store: Dict[str, Dict[str, Any]] = {}


# ==================== API ENDPOINTS ====================

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "online",
        "service": "AI Patent Diagram Generator",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "claude_agent": "configured" if claude_agent else "not_configured",
        "storage_path": str(STORAGE_PATH),
        "active_jobs": len([j for j in job_store.values() if j.get("status") == "processing"])
    }


@app.post("/api/diagram/create", response_model=DiagramStatusResponse)
async def create_diagram(request: DiagramCreateRequest, background_tasks: BackgroundTasks):
    """
    Create a new diagram from a natural language prompt.

    Args:
        request: Diagram creation request with prompt and options

    Returns:
        Job status with job_id for tracking
    """
    if not claude_agent:
        raise HTTPException(status_code=503, detail="AI service not configured")

    # Generate unique job ID
    job_id = str(uuid.uuid4())
    session_id = request.session_id or job_id

    logger.info(f"Creating diagram job {job_id} for session {session_id}")

    # Initialize job in store
    job_store[job_id] = {
        "job_id": job_id,
        "session_id": session_id,
        "status": "queued",
        "prompt": request.prompt,
        "created_at": datetime.utcnow().isoformat(),
        "progress": 0
    }

    # Queue the diagram generation task
    background_tasks.add_task(
        generate_diagram_sync,
        job_id=job_id,
        prompt=request.prompt,
        session_id=session_id,
        options=request.options
    )

    return DiagramStatusResponse(
        job_id=job_id,
        session_id=session_id,
        status=JobStatus.QUEUED,
        message="Diagram generation queued"
    )


@app.post("/api/diagram/refine", response_model=DiagramStatusResponse)
async def refine_diagram(request: DiagramRefineRequest, background_tasks: BackgroundTasks):
    """
    Refine an existing diagram based on user feedback.

    Args:
        request: Refinement request with session_id and refinement prompt

    Returns:
        Job status for the refinement task
    """
    if not claude_agent:
        raise HTTPException(status_code=503, detail="AI service not configured")

    # Find the latest diagram for this session
    session_jobs = [j for j in job_store.values() if j.get("session_id") == request.session_id]

    if not session_jobs:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get the most recent completed job
    completed_jobs = [j for j in session_jobs if j.get("status") == "completed"]
    if not completed_jobs:
        raise HTTPException(status_code=400, detail="No completed diagram found for this session")

    latest_job = max(completed_jobs, key=lambda x: x.get("created_at", ""))

    # Create new job for refinement
    job_id = str(uuid.uuid4())

    logger.info(f"Refining diagram: job {job_id}, session {request.session_id}")

    job_store[job_id] = {
        "job_id": job_id,
        "session_id": request.session_id,
        "status": "queued",
        "prompt": request.refinement_prompt,
        "parent_job_id": latest_job.get("job_id"),
        "created_at": datetime.utcnow().isoformat(),
        "progress": 0,
        "type": "refinement"
    }

    # Queue refinement task
    background_tasks.add_task(
        refine_diagram_sync,
        job_id=job_id,
        session_id=request.session_id,
        current_spec=latest_job.get("diagram_spec"),
        refinement_prompt=request.refinement_prompt
    )

    return DiagramStatusResponse(
        job_id=job_id,
        session_id=request.session_id,
        status=JobStatus.QUEUED,
        message="Diagram refinement queued"
    )


@app.get("/api/diagram/status/{job_id}", response_model=DiagramStatusResponse)
async def get_diagram_status(job_id: str):
    """
    Get the status of a diagram generation job.

    Args:
        job_id: The job identifier

    Returns:
        Current job status and details
    """
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found")

    job = job_store[job_id]

    response = DiagramStatusResponse(
        job_id=job_id,
        session_id=job.get("session_id"),
        status=job.get("status"),
        message=job.get("message", ""),
        progress=job.get("progress", 0)
    )

    if job.get("status") == "completed":
        response.download_url = f"/api/diagram/download/{job_id}.pptx"
        if job.get("preview_path"):
            response.preview_url = f"/api/diagram/preview/{job_id}.png"

    if job.get("status") == "failed":
        response.error = job.get("error")

    return response


@app.get("/api/diagram/download/{filename}")
async def download_diagram(filename: str):
    """
    Download a generated PPTX file.

    Args:
        filename: The filename (job_id.pptx)

    Returns:
        PPTX file for download
    """
    file_path = STORAGE_PATH / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.get("/api/diagram/preview/{filename}")
async def get_diagram_preview(filename: str):
    """
    Get a preview image of the diagram.

    Args:
        filename: The preview filename (job_id.png)

    Returns:
        PNG preview image
    """
    file_path = PREVIEW_PATH / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Preview not found")

    return FileResponse(
        path=file_path,
        media_type="image/png",
        filename=filename
    )


@app.get("/api/session/{session_id}/history")
async def get_session_history(session_id: str):
    """
    Get all diagrams generated in a session.

    Args:
        session_id: The session identifier

    Returns:
        List of all jobs for this session
    """
    session_jobs = [j for j in job_store.values() if j.get("session_id") == session_id]

    if not session_jobs:
        raise HTTPException(status_code=404, detail="Session not found")

    # Sort by creation time
    session_jobs.sort(key=lambda x: x.get("created_at", ""))

    return {
        "session_id": session_id,
        "total_diagrams": len(session_jobs),
        "jobs": [
            {
                "job_id": j["job_id"],
                "status": j["status"],
                "prompt": j.get("prompt", ""),
                "created_at": j.get("created_at"),
                "download_url": f"/api/diagram/download/{j['job_id']}.pptx" if j.get("status") == "completed" else None
            }
            for j in session_jobs
        ]
    }


@app.delete("/api/diagram/{job_id}")
async def delete_diagram(job_id: str):
    """
    Delete a generated diagram and its files.

    Args:
        job_id: The job identifier

    Returns:
        Deletion confirmation
    """
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found")

    # Delete files
    pptx_path = STORAGE_PATH / f"{job_id}.pptx"
    preview_path = PREVIEW_PATH / f"{job_id}.png"

    if pptx_path.exists():
        pptx_path.unlink()

    if preview_path.exists():
        preview_path.unlink()

    # Remove from store
    del job_store[job_id]

    logger.info(f"Deleted diagram job {job_id}")

    return {"message": "Diagram deleted successfully", "job_id": job_id}


@app.get("/api/stats")
async def get_statistics():
    """
    Get system statistics.

    Returns:
        Statistics about diagram generation
    """
    total_jobs = len(job_store)
    completed = len([j for j in job_store.values() if j.get("status") == "completed"])
    processing = len([j for j in job_store.values() if j.get("status") == "processing"])
    failed = len([j for j in job_store.values() if j.get("status") == "failed"])

    return {
        "total_jobs": total_jobs,
        "completed": completed,
        "processing": processing,
        "failed": failed,
        "success_rate": (completed / total_jobs * 100) if total_jobs > 0 else 0
    }


# ==================== BACKGROUND TASKS ====================

def generate_diagram_sync(
    job_id: str,
    prompt: str,
    session_id: str,
    options: Optional[Dict[str, Any]] = None
):
    """
    Synchronous diagram generation task (runs in background).

    Args:
        job_id: Job identifier
        prompt: User's diagram prompt
        session_id: Session identifier
        options: Optional generation options
    """
    try:
        logger.info(f"[JOB {job_id}] Starting diagram generation")
        logger.info(f"[JOB {job_id}] Prompt: {prompt[:200]}...")

        # Update status
        job_store[job_id]["status"] = "processing"
        job_store[job_id]["message"] = "Analyzing prompt with AI..."
        job_store[job_id]["progress"] = 10

        # Step 1: Generate spec with Claude
        logger.info(f"[JOB {job_id}] Calling Claude API...")
        spec = claude_agent.generate_diagram_spec(prompt)
        logger.info(f"[JOB {job_id}] Claude response received, elements: {len(spec.get('elements', []))}")

        job_store[job_id]["diagram_spec"] = spec
        job_store[job_id]["progress"] = 50
        job_store[job_id]["message"] = "Building PowerPoint diagram..."

        # Step 2: Generate PPTX with python-pptx
        logger.info(f"[JOB {job_id}] Generating PPTX...")
        generator = PPTXDiagramGenerator()
        generator.create_from_json(spec)

        # Save file
        output_path = STORAGE_PATH / f"{job_id}.pptx"
        generator.save(str(output_path))
        logger.info(f"[JOB {job_id}] PPTX saved to {output_path}")

        job_store[job_id]["progress"] = 90
        job_store[job_id]["message"] = "Finalizing..."

        # Generate preview (optional)
        # TODO: Convert first slide to PNG preview

        # Mark as completed
        job_store[job_id]["status"] = "completed"
        job_store[job_id]["progress"] = 100
        job_store[job_id]["message"] = "Diagram ready for download"
        job_store[job_id]["file_path"] = str(output_path)
        job_store[job_id]["completed_at"] = datetime.utcnow().isoformat()

        logger.info(f"[JOB {job_id}] ✅ Diagram generation completed successfully")

    except Exception as e:
        logger.error(f"[JOB {job_id}] ❌ Error generating diagram: {e}", exc_info=True)
        logger.error(f"[JOB {job_id}] Error type: {type(e).__name__}")
        logger.error(f"[JOB {job_id}] Error details: {str(e)}")

        job_store[job_id]["status"] = "failed"
        job_store[job_id]["error"] = f"{type(e).__name__}: {str(e)}"
        job_store[job_id]["message"] = "Diagram generation failed"


def refine_diagram_sync(
    job_id: str,
    session_id: str,
    current_spec: Dict[str, Any],
    refinement_prompt: str
):
    """
    Synchronous diagram refinement task.

    Args:
        job_id: New job identifier
        session_id: Session identifier
        current_spec: Current diagram specification
        refinement_prompt: User's refinement request
    """
    try:
        logger.info(f"Starting diagram refinement for job {job_id}")

        job_store[job_id]["status"] = "processing"
        job_store[job_id]["message"] = "Analyzing refinement request..."
        job_store[job_id]["progress"] = 10

        # Step 1: Refine spec with Claude
        refined_spec = claude_agent.refine_diagram_spec(current_spec, refinement_prompt)

        job_store[job_id]["diagram_spec"] = refined_spec
        job_store[job_id]["progress"] = 50
        job_store[job_id]["message"] = "Rebuilding diagram..."

        # Step 2: Generate updated PPTX
        generator = PPTXDiagramGenerator()
        generator.create_from_json(refined_spec)

        output_path = STORAGE_PATH / f"{job_id}.pptx"
        generator.save(str(output_path))

        # Mark as completed
        job_store[job_id]["status"] = "completed"
        job_store[job_id]["progress"] = 100
        job_store[job_id]["message"] = "Refined diagram ready"
        job_store[job_id]["file_path"] = str(output_path)
        job_store[job_id]["completed_at"] = datetime.utcnow().isoformat()

        logger.info(f"Diagram refinement completed for job {job_id}")

    except Exception as e:
        logger.error(f"Error refining diagram for job {job_id}: {e}", exc_info=True)

        job_store[job_id]["status"] = "failed"
        job_store[job_id]["error"] = str(e)
        job_store[job_id]["message"] = "Refinement failed"


# ==================== STARTUP/SHUTDOWN ====================

@app.on_event("startup")
async def startup_event():
    """Application startup tasks."""
    logger.info("=" * 60)
    logger.info("AI Patent Diagram Generator - Starting Up")
    logger.info("=" * 60)
    logger.info(f"Storage path: {STORAGE_PATH}")
    logger.info(f"Claude agent: {'Configured' if claude_agent else 'NOT CONFIGURED'}")
    logger.info(f"Allowed origins: {ALLOWED_ORIGINS}")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks."""
    logger.info("AI Patent Diagram Generator - Shutting Down")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("BACKEND_PORT", 8000))
    reload = os.getenv("BACKEND_RELOAD", "true").lower() == "true"

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=reload,
        log_level="info"
    )
