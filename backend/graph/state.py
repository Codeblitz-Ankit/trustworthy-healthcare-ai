"""State schemas and data structures for LangGraph.

Maintains the shared state and typed dictionaries tracked across all verification
and processing nodes within the healthcare verification pipeline.
"""

from typing import List, TypedDict


class FlaggedClaim(TypedDict):
    """Schema for claims flagged during safety or grounding verification."""

    claim: str
    gate_failed: str
    reason: str


class FinalResponse(TypedDict):
    """Schema for the finalized pipeline response."""

    status: str
    content: str
    sources: List[str]


class HealthcareState(TypedDict):
    """Core state tracked across the healthcare AI verification graph."""

    patient_query: str
    draft_answer: str
    claims: List[str]
    verified_claims: List[str]
    flagged_claims: List[dict]
    final_response: dict
    review_required: bool
