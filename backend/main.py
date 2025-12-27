"""
FastAPI Backend for AI Patent Diagram Generator

Main application entry point with REST API endpoints.

Author: AI Patent Diagram Generator
License: MIT
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import os
import uuid
import logging
import base64
import asyncio
from pathlib import Path
from datetime import datetime

# Import our modules
from ai.claude_agent import ClaudeDiagramAgent
from diagram_engine.pptx_generator import PPTXDiagramGenerator
from diagram_engine.elk_layout import ELKLayoutEngine, apply_elk_layout
from validation_agent import DiagramValidator, ValidationLoop, validate_diagram
from conversation_memory import memory_manager, ConversationMemory
from feedback_processor import feedback_processor, feedback_refiner, IdentifiedIssue
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

# CORS Configuration - allow all common dev ports and production domains
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:5174,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:5174"
).split(",")

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
        model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5"),
        max_tokens=int(os.getenv("ANTHROPIC_MAX_TOKENS", "16000"))
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
        "version": "1.0.2",  # Added debug endpoint to inspect Claude specs
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
        # Include the diagram spec for frontend to render
        if job.get("diagram_spec"):
            response.spec = job.get("diagram_spec")
            elements = job["diagram_spec"].get("elements", [])
            response.element_count = len(elements)
            response.diagram_type = job["diagram_spec"].get("metadata", {}).get("diagram_type", "diagram")

    if job.get("status") == "failed":
        response.error = job.get("error")

    return response


@app.get("/api/diagram/debug/{job_id}")
async def debug_diagram_spec(job_id: str):
    """
    DEBUG ENDPOINT: Get the raw diagram spec from Claude.
    This helps diagnose what Claude is actually returning.
    """
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found")

    job = job_store[job_id]
    spec = job.get("diagram_spec", {})

    return {
        "job_id": job_id,
        "status": job.get("status"),
        "spec": spec,
        "element_count": len(spec.get("elements", [])),
        "elements_preview": spec.get("elements", [])[:3]  # First 3 elements
    }


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


class ExportPPTXRequest(BaseModel):
    """Request model for exporting canvas data to PPTX."""
    spec: Dict[str, Any] = Field(..., description="Diagram specification from web editor")


@app.post("/api/diagram/export-pptx", response_model=DiagramStatusResponse)
async def export_to_pptx(request: ExportPPTXRequest, background_tasks: BackgroundTasks):
    """
    Export web editor canvas data to an editable PowerPoint file.

    This endpoint receives the diagram specification from the web-based
    diagram builder and converts it to a fully editable PPTX file.

    Args:
        request: Export request containing the diagram spec

    Returns:
        Job status with job_id for tracking
    """
    job_id = str(uuid.uuid4())

    logger.info(f"[EXPORT {job_id}] Starting PPTX export from web editor")
    logger.info(f"[EXPORT {job_id}] Elements: {len(request.spec.get('elements', []))}")
    logger.info(f"[EXPORT {job_id}] Connectors: {len(request.spec.get('connectors', []))}")

    # Initialize job in store
    job_store[job_id] = {
        "job_id": job_id,
        "session_id": job_id,
        "status": "queued",
        "type": "export",
        "created_at": datetime.utcnow().isoformat(),
        "progress": 0,
        "diagram_spec": request.spec
    }

    # Queue the export task
    background_tasks.add_task(
        export_pptx_sync,
        job_id=job_id,
        spec=request.spec
    )

    return DiagramStatusResponse(
        job_id=job_id,
        session_id=job_id,
        status=JobStatus.QUEUED,
        message="PPTX export queued"
    )


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


# ==================== HUMAN FEEDBACK ENDPOINTS ====================

class FeedbackRequest(BaseModel):
    """Request model for human feedback."""
    session_id: str = Field(..., description="Session identifier")
    feedback_text: str = Field(..., description="User's text feedback about the diagram")
    screenshot_base64: Optional[str] = Field(None, description="Base64-encoded screenshot of the diagram")


class FeedbackResponse(BaseModel):
    """Response model for feedback processing."""
    success: bool
    message: str
    identified_issues: List[Dict[str, Any]] = []
    refinement_job_id: Optional[str] = None


@app.post("/api/feedback/submit", response_model=FeedbackResponse)
async def submit_feedback(request: FeedbackRequest, background_tasks: BackgroundTasks):
    """
    Submit human feedback about a generated diagram.

    This endpoint:
    1. Analyzes the feedback text
    2. Analyzes the screenshot using Claude Vision (if provided)
    3. Identifies specific issues
    4. Queues a refinement job

    Args:
        request: Feedback request with text and optional screenshot

    Returns:
        Feedback response with identified issues and refinement job ID
    """
    if not claude_agent:
        raise HTTPException(status_code=503, detail="AI service not configured")

    logger.info(f"[FEEDBACK] Received feedback for session {request.session_id}")
    logger.info(f"[FEEDBACK] Text: {request.feedback_text[:100]}...")
    logger.info(f"[FEEDBACK] Has screenshot: {request.screenshot_base64 is not None}")

    try:
        # Process the feedback
        feedback, issues = await feedback_processor.process_feedback(
            session_id=request.session_id,
            feedback_text=request.feedback_text,
            screenshot_base64=request.screenshot_base64
        )

        logger.info(f"[FEEDBACK] Identified {len(issues)} issues")

        # Create refinement job
        job_id = str(uuid.uuid4())

        job_store[job_id] = {
            "job_id": job_id,
            "session_id": request.session_id,
            "status": "queued",
            "type": "feedback_refinement",
            "created_at": datetime.utcnow().isoformat(),
            "progress": 0,
            "feedback_text": request.feedback_text,
            "identified_issues": [i.to_dict() for i in issues]
        }

        # Queue the refinement task
        background_tasks.add_task(
            refine_from_feedback_sync,
            job_id=job_id,
            session_id=request.session_id,
            feedback=feedback,
            issues=issues
        )

        return FeedbackResponse(
            success=True,
            message=f"Feedback received. Identified {len(issues)} issues. Refinement in progress.",
            identified_issues=[i.to_dict() for i in issues],
            refinement_job_id=job_id
        )

    except Exception as e:
        logger.error(f"[FEEDBACK] Error processing feedback: {e}", exc_info=True)
        return FeedbackResponse(
            success=False,
            message=f"Error processing feedback: {str(e)}",
            identified_issues=[]
        )


@app.post("/api/feedback/upload-screenshot")
async def upload_screenshot(
    session_id: str = Form(...),
    feedback_text: str = Form(""),
    screenshot: UploadFile = File(...)
):
    """
    Upload a screenshot for feedback (multipart form).

    Alternative to submit_feedback that accepts file upload.

    Args:
        session_id: Session identifier
        feedback_text: User's text feedback
        screenshot: Uploaded screenshot file

    Returns:
        Feedback response with analysis results
    """
    if not claude_agent:
        raise HTTPException(status_code=503, detail="AI service not configured")

    logger.info(f"[FEEDBACK] Screenshot upload for session {session_id}")
    logger.info(f"[FEEDBACK] File: {screenshot.filename}, Content-Type: {screenshot.content_type}")

    try:
        # Read and encode the screenshot
        contents = await screenshot.read()
        screenshot_base64 = base64.b64encode(contents).decode('utf-8')

        # Process the feedback
        feedback, issues = await feedback_processor.process_feedback(
            session_id=session_id,
            feedback_text=feedback_text or "Please analyze this diagram and fix any issues.",
            screenshot_base64=screenshot_base64
        )

        return {
            "success": True,
            "message": f"Screenshot analyzed. Found {len(issues)} issues.",
            "identified_issues": [i.to_dict() for i in issues],
            "screenshot_analysis": feedback.screenshot_analysis
        }

    except Exception as e:
        logger.error(f"[FEEDBACK] Error processing screenshot: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/session/{session_id}/memory")
async def get_session_memory(session_id: str):
    """
    Get the conversation memory for a session.

    Returns the full context that the LLM has about this conversation.

    Args:
        session_id: Session identifier

    Returns:
        Session memory including messages, diagram versions, and feedback
    """
    memory = memory_manager.get(session_id)

    if not memory:
        raise HTTPException(status_code=404, detail="Session memory not found")

    context = memory.get_context_for_llm(include_full_history=True)

    return {
        "session_id": session_id,
        "memory_summary": memory.to_dict(),
        "context": context,
        "message_count": len(memory.messages),
        "diagram_versions": len(memory.diagram_versions),
        "feedback_count": len(memory.feedback_history)
    }


@app.delete("/api/session/{session_id}/memory")
async def clear_session_memory(session_id: str):
    """
    Clear the conversation memory for a session.

    This resets the LLM's context for this session.

    Args:
        session_id: Session identifier

    Returns:
        Confirmation message
    """
    if memory_manager.delete(session_id):
        return {"success": True, "message": f"Memory cleared for session {session_id}"}
    else:
        raise HTTPException(status_code=404, detail="Session memory not found")


class ChatMessage(BaseModel):
    """A chat message in the conversation."""
    session_id: str
    message: str
    include_diagram_context: bool = True


@app.post("/api/chat")
async def chat_with_context(request: ChatMessage):
    """
    Send a chat message with full diagram context.

    This endpoint allows natural language conversation about the diagram
    while maintaining full context awareness.

    Args:
        request: Chat message with session context

    Returns:
        AI response based on conversation history
    """
    if not claude_agent:
        raise HTTPException(status_code=503, detail="AI service not configured")

    memory = memory_manager.get_or_create(request.session_id)

    # Add user message to memory
    memory.add_user_message(content=request.message)

    # Get context for LLM
    context = memory.get_context_for_llm()

    # Build prompt with context
    system_prompt = """You are an AI assistant helping with diagram creation.
You have full context of the conversation and can see the diagram specifications.
Be helpful and specific about diagram modifications."""

    user_prompt = f"""Context about the current diagram and conversation:
{context}

User's message: {request.message}

Please respond helpfully. If they're asking to modify the diagram, explain what changes would be needed."""

    try:
        # Call Claude for response
        import anthropic
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

        response = client.messages.create(
            model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250514"),
            max_tokens=2000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        assistant_response = response.content[0].text

        # Add assistant response to memory
        memory.add_assistant_message(content=assistant_response)

        return {
            "response": assistant_response,
            "session_id": request.session_id,
            "message_count": len(memory.messages)
        }

    except Exception as e:
        logger.error(f"[CHAT] Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==================== BACKGROUND TASKS ====================

def generate_diagram_sync(
    job_id: str,
    prompt: str,
    session_id: str,
    options: Optional[Dict[str, Any]] = None
):
    """
    V2 Diagram generation with ELK layout and validation loop.

    Pipeline:
    1. Claude generates logical structure (nodes + edges with hints)
    2. ELK Layout Engine calculates positions with collision detection
    3. Validation loop checks for overlaps and missing connections
    4. PPTX generator creates the final PowerPoint file
    5. Store in conversation memory for feedback loop

    Args:
        job_id: Job identifier
        prompt: User's diagram prompt
        session_id: Session identifier
        options: Optional generation options
    """
    try:
        logger.info(f"[JOB {job_id}] Starting V2 diagram generation")
        logger.info(f"[JOB {job_id}] Prompt: {prompt[:200]}...")

        # Initialize conversation memory for this session
        memory = memory_manager.get_or_create(session_id)
        memory.add_user_message(content=prompt)

        # Update status
        job_store[job_id]["status"] = "processing"
        job_store[job_id]["message"] = "Analyzing prompt with AI..."
        job_store[job_id]["progress"] = 10

        # Step 1: Generate V2 spec with Claude (nodes + edges, no coordinates)
        logger.info(f"[JOB {job_id}] Calling Claude V2 API...")
        v2_spec = claude_agent.generate_diagram_spec_v2(prompt)
        logger.info(f"[JOB {job_id}] Claude V2 response: {len(v2_spec.get('nodes', []))} nodes, {len(v2_spec.get('edges', []))} edges")

        job_store[job_id]["v2_spec"] = v2_spec  # Keep original V2 spec for debugging
        job_store[job_id]["progress"] = 30
        job_store[job_id]["message"] = "Calculating optimal layout..."

        # Step 2: Apply ELK layout with validation loop
        logger.info(f"[JOB {job_id}] Running ELK layout engine...")
        layout_engine = ELKLayoutEngine()
        validator = DiagramValidator()
        validation_loop = ValidationLoop(layout_engine, validator)

        # Run layout with validation (up to 3 attempts)
        v1_spec, validation_issues = validation_loop.generate_with_validation(v2_spec)

        # Log validation results
        errors = [i for i in validation_issues if i.severity == 'error']
        warnings = [i for i in validation_issues if i.severity == 'warning']
        logger.info(f"[JOB {job_id}] Layout complete: {len(errors)} errors, {len(warnings)} warnings")

        if errors:
            logger.warning(f"[JOB {job_id}] Validation errors: {[e.message for e in errors]}")

        job_store[job_id]["diagram_spec"] = v1_spec
        job_store[job_id]["validation_issues"] = [
            {"type": i.issue_type, "severity": i.severity, "message": i.message}
            for i in validation_issues
        ]
        job_store[job_id]["progress"] = 60
        job_store[job_id]["message"] = "Building PowerPoint diagram..."

        # Step 3: Generate PPTX with python-pptx
        logger.info(f"[JOB {job_id}] Generating PPTX with {len(v1_spec.get('elements', []))} elements...")
        generator = PPTXDiagramGenerator()
        generator.create_from_json(v1_spec)

        # Save file
        output_path = STORAGE_PATH / f"{job_id}.pptx"
        generator.save(str(output_path))
        logger.info(f"[JOB {job_id}] PPTX saved to {output_path}")

        job_store[job_id]["progress"] = 90
        job_store[job_id]["message"] = "Finalizing..."

        # Step 4: Store in conversation memory for feedback loop
        memory.add_diagram_version(
            version_id=job_id,
            v2_spec=v2_spec,
            v1_spec=v1_spec,
            validation_issues=[
                {"type": i.issue_type, "severity": i.severity, "message": i.message}
                for i in validation_issues
            ],
            prompt=prompt,
            is_refinement=False
        )

        memory.add_assistant_message(
            content=f"Generated diagram with {len(v2_spec.get('nodes', []))} nodes and {len(v2_spec.get('edges', []))} edges.",
            metadata={"job_id": job_id}
        )

        # Mark as completed
        job_store[job_id]["status"] = "completed"
        job_store[job_id]["progress"] = 100
        job_store[job_id]["message"] = "Diagram ready for download"
        job_store[job_id]["file_path"] = str(output_path)
        job_store[job_id]["completed_at"] = datetime.utcnow().isoformat()

        logger.info(f"[JOB {job_id}] ✅ V2 diagram generation completed successfully")

    except Exception as e:
        logger.error(f"[JOB {job_id}] ❌ Error generating diagram: {e}", exc_info=True)
        logger.error(f"[JOB {job_id}] Error type: {type(e).__name__}")
        logger.error(f"[JOB {job_id}] Error details: {str(e)}")

        job_store[job_id]["status"] = "failed"
        job_store[job_id]["error"] = f"{type(e).__name__}: {str(e)}"
        job_store[job_id]["message"] = "Diagram generation failed"


def export_pptx_sync(job_id: str, spec: Dict[str, Any]):
    """
    Synchronous PPTX export task (runs in background).

    Converts web editor canvas data to an editable PowerPoint file.

    Args:
        job_id: Job identifier
        spec: Diagram specification from web editor
    """
    try:
        logger.info(f"[EXPORT {job_id}] Processing PPTX export")

        job_store[job_id]["status"] = "processing"
        job_store[job_id]["message"] = "Building PowerPoint diagram..."
        job_store[job_id]["progress"] = 30

        # Generate PPTX with python-pptx
        generator = PPTXDiagramGenerator()
        generator.create_from_json(spec)

        job_store[job_id]["progress"] = 70
        job_store[job_id]["message"] = "Saving file..."

        # Save file
        output_path = STORAGE_PATH / f"{job_id}.pptx"
        generator.save(str(output_path))

        logger.info(f"[EXPORT {job_id}] PPTX saved to {output_path}")

        # Mark as completed
        job_store[job_id]["status"] = "completed"
        job_store[job_id]["progress"] = 100
        job_store[job_id]["message"] = "Export ready for download"
        job_store[job_id]["file_path"] = str(output_path)
        job_store[job_id]["completed_at"] = datetime.utcnow().isoformat()

        logger.info(f"[EXPORT {job_id}] PPTX export completed successfully")

    except Exception as e:
        logger.error(f"[EXPORT {job_id}] Error exporting PPTX: {e}", exc_info=True)

        job_store[job_id]["status"] = "failed"
        job_store[job_id]["error"] = f"{type(e).__name__}: {str(e)}"
        job_store[job_id]["message"] = "Export failed"


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


def refine_from_feedback_sync(
    job_id: str,
    session_id: str,
    feedback,  # HumanFeedback object
    issues: List  # List of IdentifiedIssue
):
    """
    Refine diagram based on human feedback with screenshot analysis.

    This is the core of the human feedback loop:
    1. Uses conversation memory for full context
    2. Applies identified issues from feedback
    3. Regenerates the diagram with fixes

    Args:
        job_id: Job identifier
        session_id: Session identifier
        feedback: HumanFeedback object with text and screenshot analysis
        issues: List of IdentifiedIssue objects
    """
    try:
        logger.info(f"[FEEDBACK JOB {job_id}] Starting feedback-based refinement")
        logger.info(f"[FEEDBACK JOB {job_id}] Session: {session_id}, Issues: {len(issues)}")

        job_store[job_id]["status"] = "processing"
        job_store[job_id]["message"] = "Analyzing feedback with full context..."
        job_store[job_id]["progress"] = 10

        # Get conversation memory
        memory = memory_manager.get(session_id)
        if not memory:
            raise ValueError(f"No memory found for session {session_id}")

        latest_version = memory.get_latest_diagram_version()
        if not latest_version:
            raise ValueError(f"No diagram found in session {session_id}")

        job_store[job_id]["progress"] = 20
        job_store[job_id]["message"] = "Reasoning about required changes..."

        # Use the async refiner in a sync context
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            refined_v2_spec = loop.run_until_complete(
                feedback_refiner.refine_diagram(
                    session_id=session_id,
                    feedback=feedback,
                    issues=issues
                )
            )
        finally:
            loop.close()

        logger.info(f"[FEEDBACK JOB {job_id}] Got refined V2 spec with {len(refined_v2_spec.get('nodes', []))} nodes")

        job_store[job_id]["v2_spec"] = refined_v2_spec
        job_store[job_id]["progress"] = 40
        job_store[job_id]["message"] = "Calculating new layout..."

        # Apply ELK layout with validation
        layout_engine = ELKLayoutEngine()
        validator = DiagramValidator()
        validation_loop = ValidationLoop(layout_engine, validator)

        v1_spec, validation_issues = validation_loop.generate_with_validation(refined_v2_spec)

        errors = [i for i in validation_issues if i.severity == 'error']
        logger.info(f"[FEEDBACK JOB {job_id}] Layout complete: {len(errors)} errors")

        job_store[job_id]["diagram_spec"] = v1_spec
        job_store[job_id]["validation_issues"] = [
            {"type": i.issue_type, "severity": i.severity, "message": i.message}
            for i in validation_issues
        ]
        job_store[job_id]["progress"] = 70
        job_store[job_id]["message"] = "Generating PowerPoint..."

        # Generate PPTX
        generator = PPTXDiagramGenerator()
        generator.create_from_json(v1_spec)

        output_path = STORAGE_PATH / f"{job_id}.pptx"
        generator.save(str(output_path))

        logger.info(f"[FEEDBACK JOB {job_id}] PPTX saved to {output_path}")

        # Update conversation memory with new version
        memory.add_diagram_version(
            version_id=job_id,
            v2_spec=refined_v2_spec,
            v1_spec=v1_spec,
            validation_issues=[
                {"type": i.issue_type, "severity": i.severity, "message": i.message}
                for i in validation_issues
            ],
            prompt=feedback.feedback_text,
            is_refinement=True,
            parent_version_id=latest_version.version_id
        )

        # Mark as completed
        job_store[job_id]["status"] = "completed"
        job_store[job_id]["progress"] = 100
        job_store[job_id]["message"] = "Diagram refined based on your feedback"
        job_store[job_id]["file_path"] = str(output_path)
        job_store[job_id]["completed_at"] = datetime.utcnow().isoformat()
        job_store[job_id]["issues_addressed"] = len(issues)

        logger.info(f"[FEEDBACK JOB {job_id}] ✅ Feedback refinement completed successfully")

    except Exception as e:
        logger.error(f"[FEEDBACK JOB {job_id}] ❌ Error: {e}", exc_info=True)

        job_store[job_id]["status"] = "failed"
        job_store[job_id]["error"] = f"{type(e).__name__}: {str(e)}"
        job_store[job_id]["message"] = "Feedback refinement failed"


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
