"""FastAPI backend for the Governed AI Content Pipeline."""

import os
import sys
from pathlib import Path

parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from schemas.models import RunArtifact
from storage.store import ArtifactStore


class GenerateRequest(BaseModel):
    grade: int
    topic: str
    user_id: Optional[str] = None


class GenerateResponse(BaseModel):
    run_id: str
    status: str
    final_status: str
    content: Optional[dict] = None
    tags: Optional[dict] = None


class HistoryResponse(BaseModel):
    total_count: int
    artifacts: List[dict]


app = FastAPI(
    title="Governed AI Content Pipeline",
    description="Production-grade content generation with strict validation, quantitative evaluation, and full auditability",
    version="1.0.0",
)

store = ArtifactStore()

_orchestrator = None


def get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=503,
                detail="OpenAI API key not configured. Set OPENAI_API_KEY environment variable."
            )
        from agents.orchestrator import Orchestrator
        _orchestrator = Orchestrator(api_key=api_key)
    return _orchestrator


@app.post("/generate", response_model=GenerateResponse)
async def generate_content(request: GenerateRequest) -> GenerateResponse:
    try:
        orchestrator = get_orchestrator()

        artifact = orchestrator.execute(
            grade=request.grade,
            topic=request.topic,
            user_id=request.user_id,
        )

        store.store(artifact)

        final_content = artifact.final.content.model_dump() if artifact.final.content else None
        final_tags = artifact.final.tags.model_dump() if artifact.final.tags else None

        return GenerateResponse(
            run_id=artifact.run_id,
            status="success",
            final_status=artifact.final.status.value,
            content=final_content,
            tags=final_tags,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline execution failed: {str(e)}"
        )


@app.get("/history", response_model=HistoryResponse)
async def get_history(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    limit: int = Query(100, ge=1, le=1000, description="Max results"),
    offset: int = Query(0, ge=0, description="Number to skip"),
) -> HistoryResponse:
    try:
        if user_id:
            artifacts = store.get_by_user_id(user_id, limit=limit, offset=offset)
            total_count = store.count_by_user(user_id)
        else:
            artifacts = store.list_all(limit=limit, offset=offset)
            total_count = store.count_total()

        artifact_dicts = [a.model_dump() for a in artifacts]

        return HistoryResponse(
            total_count=total_count,
            artifacts=artifact_dicts,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve history: {str(e)}"
        )


@app.get("/artifact/{run_id}")
async def get_artifact(run_id: str):
    try:
        artifact = store.get_by_run_id(run_id)
        if not artifact:
            raise HTTPException(
                status_code=404,
                detail=f"Artifact with run_id '{run_id}' not found"
            )
        return artifact.model_dump()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve artifact: {str(e)}"
        )


@app.get("/health")
async def health_check():
    api_key = os.getenv("OPENAI_API_KEY")
    return {
        "status": "healthy",
        "service": "Governed AI Content Pipeline",
        "openai_configured": "yes" if api_key else "no",
    }


@app.get("/stats")
async def get_stats():
    return {
        "total_artifacts": store.count_total(),
        "status": "operational",
    }


@app.get("/")
async def root():
    return {
        "service": "Governed AI Content Pipeline",
        "version": "1.0.0",
        "endpoints": {
            "POST /generate": "Generate content through full pipeline",
            "GET /history": "Retrieve artifact history",
            "GET /artifact/{run_id}": "Get specific artifact",
            "GET /health": "Health check",
            "GET /stats": "Pipeline statistics",
            "GET /docs": "Interactive API documentation (Swagger UI)",
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
