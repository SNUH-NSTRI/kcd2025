"""Streaming report generation endpoints."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, Request, HTTPException, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from rwe_api.config import settings  # Centralized config
# Import the new service
from ..services import report_generator_service

router = APIRouter()

# Use centralized config (ALWAYS loads .env)
PROJECT_ROOT = settings.PROJECT_ROOT


class ReportStreamRequest(BaseModel):
    """Request model for streaming report generation."""

    nct_id: str
    medication: str


@router.options("/stream")
async def stream_report_options():
    """Handle CORS preflight for streaming endpoint."""
    return {}


@router.post("/stream")
async def stream_report(request: Request, body: ReportStreamRequest = Body(...)):
    """
    Stream comprehensive report generation using Server-Sent Events (SSE).

    This endpoint yields report sections progressively as they are generated,
    allowing real-time rendering on the frontend. Now uses LLM for
    insightful report creation.

    Args:
        request: FastAPI request object (for disconnect detection)
        body: Report request with nct_id and medication

    Returns:
        StreamingResponse with text/event-stream content
    """

    async def event_generator():
        """Generate SSE events for report sections."""
        try:
            # Log received parameters for debugging
            print(f"[STREAM] Received request - NCT ID: {body.nct_id}, Medication: '{body.medication}'")

            # Yield initial status
            yield f"data: {json.dumps({'type': 'status', 'message': 'Starting AI-powered report generation...'})}\n\n"
            await asyncio.sleep(0.1)

            # Check if client is still connected
            if await request.is_disconnected():
                return

            # Normalize medication name to match directory naming
            normalized_medication = "".join(c for c in body.medication if c.isalnum()).lower()
            print(f"[STREAM] Normalized medication: '{body.medication}' → '{normalized_medication}'")

            # Define paths
            project_path = PROJECT_ROOT / body.nct_id
            cohort_path = project_path / "cohorts" / normalized_medication

            print(f"[STREAM] Looking for cohort at: {cohort_path}")
            if not cohort_path.exists():
                yield f"data: {json.dumps({'type': 'error', 'message': f'Cohort not found: {body.nct_id}/{body.medication}'})}\n\n"
                yield "data: [DONE]\n\n"
                return

            # Stream report sections progressively from the new service
            report_stream = report_generator_service.stream_llm_report(
                project_path, cohort_path, body.medication
            )

            async for chunk in report_stream:
                if await request.is_disconnected():
                    break

                # SSE format: send each chunk as content
                sse_data = json.dumps({'type': 'content', 'data': chunk})
                yield f"data: {sse_data}\n\n"
                await asyncio.sleep(0.02)  # Small delay for smoother streaming

            # Signal completion
            yield "data: [DONE]\n\n"

        except Exception as e:
            error_msg = f"Report generation error: {str(e)}"
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


# The old generate_report_sections function has been removed.
# Report generation is now handled by report_generator_service with LLM.
