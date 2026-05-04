"""
analyse.py
----------
POST /api/analyse  →  SSE stream of StepEvent objects
"""

import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.models.schemas import AnalyseRequest
from app.agent.pipeline import run_pipeline

router = APIRouter()


async def _event_generator(github_url: str):
    async for event in run_pipeline(github_url):
        data = json.dumps(event)
        yield f"data: {data}\n\n"
    yield "data: [DONE]\n\n"


@router.post("/analyse")
async def analyse(request: AnalyseRequest):
    return StreamingResponse(
        _event_generator(request.github_url),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
