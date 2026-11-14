"""LangGraph workflow node implementations for healthcare AI verification."""

import asyncio
import json
import os
import re
import time
from typing import Any, Dict, List

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from .state import HealthcareState

try:
    from ..gates.hard_safety import check_claim_hard_safety
    from ..gates.grounding import check_claim_grounding
    from ..gates.consistency import check_claim_consistency
    from ..gates.irrelevant_change import check_irrelevant_change
    from ..security.input_safety import sanitize_input
except (ImportError, ValueError):
    from backend.gates.hard_safety import check_claim_hard_safety
    from backend.gates.grounding import check_claim_grounding
    from backend.gates.consistency import check_claim_consistency
    from backend.gates.irrelevant_change import check_irrelevant_change
    from backend.security.input_safety import sanitize_input

load_dotenv()

PROPOSER_SYSTEM_PROMPT = (
    "You are a medical AI assistant. Answer the patient query briefly and accurately. "
    "Then, split your own answer into atomic factual claims.\n"
    "You must output a JSON object with keys 'answer' (string) and 'claims' (list of strings).\n"
    "Example format:\n"
    "{\n"
    '  "answer": "Concise medical answer.",\n'
    '  "claims": ["First atomic claim.", "Second atomic claim."]\n'
    "}"
)


def _extract_json(content: Any) -> Dict[str, Any]:
    """Parse JSON from model response content, stripping markdown fences if present."""
    text = content if isinstance(content, str) else str(content)
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


async def input_safety_node(state: HealthcareState) -> dict:
    """Sanitize and validate the patient query before it enters the reasoning pipeline.

    Redacts PHI and rejects prompt injection attempts. If the query is unsafe,
    immediately short-circuits to a not_verified final_response so the aggregator
    can terminate the pipeline cleanly.
    """
    patient_query = state.get("patient_query", "")
    result = await sanitize_input(patient_query)

    if not result.is_safe:
        # Pre-populate final_response so aggregator can pass it through
        update = {
            "patient_query": "",
            "draft_answer": "",
            "claims": [],
            "flagged_claims": [
                {
                    "claim": patient_query[:200],
                    "gate_failed": "input_safety",
                    "reason": result.reason,
                }
            ],
            "final_response": {
                "status": "not_verified",
                "content": f"Query rejected by input safety layer: {result.reason}",
                "sources": [],
            },
            "review_required": True,
        }
    else:
        update = {
            "patient_query": result.sanitized_query,
        }

    if isinstance(state, dict):
        state.update(update)

    return update


async def proposer_node(state: HealthcareState) -> dict:
    """Draft an answer using Gemini and split it into verifiable claims."""
    load_dotenv()
    patient_query = state.get("patient_query", "")

    # Short-circuit if input_safety already blocked the request
    if state.get("final_response", {}).get("status") == "not_verified":
        return {}

    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is missing or empty.")

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.0,
            google_api_key=api_key,
        )

        messages = [
            SystemMessage(content=PROPOSER_SYSTEM_PROMPT),
            HumanMessage(content=patient_query),
        ]

        response = await llm.ainvoke(messages)
        parsed = _extract_json(response.content)

        if not isinstance(parsed, dict):
            raise ValueError("LLM response did not return a valid JSON object.")

        draft_answer = str(parsed.get("answer", ""))
        raw_claims = parsed.get("claims", [])
        claims = [str(c) for c in raw_claims] if isinstance(raw_claims, list) else []

        update = {
            "draft_answer": draft_answer,
            "claims": claims,
        }
    except Exception as exc:
        update = {
            "draft_answer": "",
            "claims": [],
            "final_response": {
                "status": "not_verified",
                "content": f"Unable to generate a response because the proposer failed: {exc}",
                "sources": [],
            },
            "review_required": True,
        }

    if isinstance(state, dict):
        state.update(update)

    return update


async def hard_safety_node(state: HealthcareState) -> dict:
    """Verify claims against hard safety constraints using Z3 formal logic."""
    started_at = time.monotonic()
    if state.get("final_response", {}).get("status") == "not_verified":
        print("Gate hard_safety completed in 0.0 ms (skipped)")
        return {}

    claims = state.get("claims", [])
    existing_flagged = list(state.get("flagged_claims", []))

    passed_claims: List[str] = []
    flagged_claims: List[dict] = list(existing_flagged)

    for claim in claims:
        result = await check_claim_hard_safety(claim)
        if result.get("passed", True):
            passed_claims.append(claim)
        else:
            reason = result.get("reason", "Single dose exceeds 1000 mg limit")
            counterexample = result.get("counterexample")
            if counterexample:
                reason = f"{reason} (counterexample: {counterexample})"
            flagged_claims.append({
                "claim": claim,
                "gate_failed": result.get("gate", "hard_safety"),
                "reason": reason,
            })

    update = {
        "claims": passed_claims,
        "flagged_claims": flagged_claims,
    }

    if isinstance(state, dict):
        state.update(update)

    print(f"Gate hard_safety completed in {(time.monotonic() - started_at) * 1000:.1f} ms")
    return update


async def _run_claim_gate(
    gate_name: str,
    claims: List[str],
    checker: Any,
) -> tuple[set[str], List[dict]]:
    """Run one claim gate concurrently and return passed claims and failures."""
    started_at = time.monotonic()
    try:
        results = await asyncio.gather(*(checker(claim) for claim in claims))
        passed_claims = {
            claim for claim, result in zip(claims, results)
            if result.get("passed", True)
        }
        flagged_claims = [
            {
                "claim": claim,
                "gate_failed": result.get("gate", gate_name),
                "reason": result.get("reason", f"Failed {gate_name} review"),
            }
            for claim, result in zip(claims, results)
            if not result.get("passed", True)
        ]
        return passed_claims, flagged_claims
    finally:
        print(f"Gate {gate_name} completed in {(time.monotonic() - started_at) * 1000:.1f} ms")


async def _run_irrelevant_change_gate(
    query: str,
    claims: List[str],
) -> tuple[set[str], List[dict]]:
    """Run Gate 4 for dosage-like queries."""
    started_at = time.monotonic()
    try:
        result = await check_irrelevant_change(query, claims)
        if result.get("passed", True):
            return set(claims), []
        return set(), [
            {
                "claim": claim,
                "gate_failed": result.get("gate", "irrelevant_change"),
                "reason": result.get(
                    "reason",
                    "Clinical advice unstable under irrelevant-change test.",
                ),
            }
            for claim in claims
        ]
    finally:
        print(
            "Gate irrelevant_change completed in "
            f"{(time.monotonic() - started_at) * 1000:.1f} ms"
        )


async def verification_node(state: HealthcareState) -> dict:
    """Run the independent verification gates concurrently and merge their results."""
    if state.get("final_response", {}).get("status") == "not_verified":
        return {}

    claims = list(state.get("claims", []))
    if not claims:
        return {}

    gate_tasks = [
        _run_claim_gate("grounding", claims, check_claim_grounding),
        _run_claim_gate("consistency", claims, check_claim_consistency),
    ]
    # Gate 4 is expensive and is only needed when the query contains dosage-like data.
    if re.search(r"\d|\bmg\b", state.get("patient_query", ""), re.IGNORECASE):
        gate_tasks.append(
            _run_irrelevant_change_gate(state.get("patient_query", ""), claims)
        )
    else:
        print("Gate irrelevant_change skipped for low-risk query")

    gate_results = await asyncio.gather(*gate_tasks)
    verified_claims = set(claims)
    new_flagged = list(state.get("flagged_claims", []))
    for passed_claims, flagged_claims in gate_results:
        verified_claims.intersection_update(passed_claims)
        new_flagged.extend(flagged_claims)

    update = {
        "claims": [claim for claim in claims if claim in verified_claims],
        "flagged_claims": new_flagged,
    }
    if isinstance(state, dict):
        state.update(update)
    return update


async def aggregator_node(state: HealthcareState) -> dict:
    """Aggregate gate outcomes and synthesize final release decision and verification status."""
    # If a previous node (e.g., input_safety) already set final_response, pass it through
    existing_final = state.get("final_response", {})
    if existing_final.get("status") == "not_verified" and existing_final.get("content"):
        update = {
            "final_response": existing_final,
            "review_required": True,
            "verified_claims": [],
        }
        if isinstance(state, dict):
            state.update(update)
        return update

    claims = state.get("claims", [])
    draft_answer = state.get("draft_answer", "")
    flagged_claims = state.get("flagged_claims", [])
    gate_failures = {item.get("gate_failed") for item in flagged_claims if isinstance(item, dict)}
    hard_safety_failed = bool(gate_failures.intersection({"hard_safety", "input_safety", "safety"}))
    has_flagged = bool(flagged_claims)
    has_valid_claims = bool(claims)

    if hard_safety_failed or (has_flagged and not has_valid_claims):
        reasons = "; ".join(
            item.get("reason", "Unspecified verification failure")
            for item in flagged_claims
            if isinstance(item, dict)
        )
        final_response = {
            "status": "not_verified",
            "content": (
                "Safety Alert: The proposed AI response was withheld. "
                f"Reason: {reasons}. This query has been escalated for clinician review."
            ),
            "sources": [],
        }
    elif has_flagged and has_valid_claims:
        reasons = "; ".join(
            item.get("reason", "Unspecified verification failure")
            for item in flagged_claims
            if isinstance(item, dict)
        )
        final_response = {
            "status": "partially_verified",
            "content": (
                "Verified Claims:\n"
                f"{chr(10).join(f'- {claim}' for claim in claims)}\n\n"
                f"Withheld Claims and Reasons:\n- {reasons}"
            ),
            "sources": ["openFDA"],
        }
    else:
        final_response = {
            "status": "verified",
            "content": (
                "Verified Information: "
                f"{draft_answer} This information has been cross-checked against "
                "the FDA drug database and independent medical AI models."
            ),
            "sources": ["openFDA", "Groq Llama-3"],
        }

    review_required = has_flagged

    update = {
        "final_response": final_response,
        "review_required": review_required,
        "verified_claims": list(claims),
    }

    if isinstance(state, dict):
        state.update(update)

    return update
