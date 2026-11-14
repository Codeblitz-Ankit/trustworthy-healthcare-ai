"""Main FastAPI application entry point.

Provides the healthcare AI verification API endpoints and serves the LangGraph state machine.
Includes audit logging middleware (audit.jsonl) and end-to-end latency tracking.
"""

import asyncio
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict

try:
    from .graph.pipeline import healthcare_pipeline
    from .graph.state import HealthcareState
except (ImportError, ValueError):
    from backend.graph.pipeline import healthcare_pipeline
    from backend.graph.state import HealthcareState

load_dotenv()

# ---------------------------------------------------------------------------
# Audit log setup – backend/audit.jsonl
# ---------------------------------------------------------------------------
_AUDIT_LOG_PATH = Path(__file__).parent / "audit.jsonl"
_PIPELINE_TIMEOUT_SECONDS = 30  # Non-functional requirement: 30 s max for high-risk queries


def _write_audit_entry(entry: dict) -> None:
    """Append a single JSON line to the audit log file."""
    try:
        with _AUDIT_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass  # Never let logging failures block the API response


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Trustworthy Healthcare AI Verification API",
    description="LangGraph-powered verification pipeline enforcing clinical safety and grounding.",
    version="0.1.0",
)

# Configure CORS for frontend access (Vite default ports)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class VerifyRequest(BaseModel):
    """Request schema for healthcare query verification."""

    query: str

    model_config = ConfigDict(extra="ignore")


@app.post("/verify")
async def verify_query(request: VerifyRequest) -> Dict[str, Any]:
    """Execute the healthcare verification state machine for a patient query.

    Logs every request and response to audit.jsonl.
    Enforces a 30-second timeout; defaults to not_verified on timeout.

    Args:
        request: JSON body containing the patient query string.

    Returns:
        dict: The final_response dict plus top-level review_required flag.
    """
    start_time = time.monotonic()
    timestamp = datetime.now(timezone.utc).isoformat()

    initial_state = {
        "patient_query": request.query,
        "draft_answer": "",
        "claims": [],
        "verified_claims": [],
        "flagged_claims": [],
        "final_response": {},
        "review_required": False,
    }

    try:
        result = await asyncio.wait_for(
            healthcare_pipeline.ainvoke(initial_state),
            timeout=_PIPELINE_TIMEOUT_SECONDS,
        )
        final_response: dict = result.get("final_response", {})
        review_required: bool = bool(result.get("review_required", False))

    except asyncio.TimeoutError:
        final_response = {
            "status": "not_verified",
            "content": "Verification timed out. Defaulting to not verified for safety.",
            "sources": [],
        }
        review_required = True

    latency_ms = round((time.monotonic() - start_time) * 1000, 1)

    # Audit log entry – 100% of requests
    _write_audit_entry({
        "timestamp": timestamp,
        "query": request.query,
        "status": final_response.get("status", "unknown"),
        "review_required": review_required,
        "latency_ms": latency_ms,
    })

    # Return final_response fields + explicit review_required at the top level
    return {
        **final_response,
        "review_required": review_required,
    }
