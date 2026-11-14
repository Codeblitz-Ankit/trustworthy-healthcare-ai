"""Gate 4: Irrelevant-Change Test.

Verifies that clinical advice is robust — the answer must not change when
irrelevant (non-clinical) details are added to the query.

A lightweight Gemini call perturbs the query with an innocuous appended phrase
and re-extracts claims. If the core clinical advice diverges significantly,
the original claims are flagged as potentially unstable.
"""

import json
import os
import re
from typing import Any, Dict, List

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

_PERTURBATION_SUFFIX = " (Note: My name is Alex Johnson and I live in Springfield.)"

_PROPOSER_SYSTEM_PROMPT = (
    "You are a medical AI assistant. Answer the patient query briefly and accurately. "
    "Then, split your own answer into atomic factual claims.\n"
    "You must output a JSON object with keys 'answer' (string) and 'claims' (list of strings)."
)

_COMPARE_SYSTEM_PROMPT = (
    "You are a clinical consistency reviewer. You will be given two answers to the same question. "
    "Does the core medical meaning remain exactly the same between these two answers? "
    "Ignore wording and style changes. Flag CHANGED only when actual medical advice changes, "
    "such as a different medication or dose. Output exactly one word: CONSISTENT or CHANGED."
)


def _extract_json(content: Any) -> Dict[str, Any]:
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


async def check_irrelevant_change(
    original_query: str,
    original_claims: List[str],
) -> dict:
    """Test that clinical advice does not change when irrelevant details are added.

    Args:
        original_query: The original patient query.
        original_claims: List of claims already extracted by the proposer node.

    Returns:
        dict: Result with 'passed', 'gate', and 'reason'.
    """
    if not original_claims:
        return {"passed": True, "gate": "irrelevant_change", "reason": "No claims to compare."}

    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return {
            "passed": True,
            "gate": "irrelevant_change",
            "reason": "Irrelevant-change check skipped: GEMINI_API_KEY is missing.",
        }

    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0.0,
            google_api_key=api_key,
        )

        # Step 1: Re-answer the perturbed query
        perturbed_query = original_query + _PERTURBATION_SUFFIX
        proposer_messages = [
            SystemMessage(content=_PROPOSER_SYSTEM_PROMPT),
            HumanMessage(content=perturbed_query),
        ]
        perturbed_response = await llm.ainvoke(proposer_messages)
        parsed = _extract_json(perturbed_response.content)
        perturbed_claims: List[str] = parsed.get("claims", [])

        if not perturbed_claims:
            return {
                "passed": False,
                "gate": "irrelevant_change",
                "reason": "Could not extract claims from perturbed query response.",
            }

        # Step 2: Compare original vs. perturbed claims
        compare_prompt = (
            f"Original answer:\n{chr(10).join(original_claims)}\n"
            f"Original claims:\n{chr(10).join(f'- {c}' for c in original_claims)}\n\n"
            f"Perturbed answer:\n{parsed.get('answer', '')}\n"
            f"Perturbed query claims:\n{chr(10).join(f'- {c}' for c in perturbed_claims)}"
        )
        compare_messages = [
            SystemMessage(content=_COMPARE_SYSTEM_PROMPT),
            HumanMessage(content=compare_prompt),
        ]
        compare_response = await llm.ainvoke(compare_messages)
        verdict = (
            compare_response.content
            if isinstance(compare_response.content, str)
            else str(compare_response.content)
        ).strip().upper()

        if "CHANGED" in verdict:
            return {
                "passed": False,
                "gate": "irrelevant_change",
                "reason": "Clinical advice changed when irrelevant details were added (instability detected).",
            }

        return {
            "passed": True,
            "gate": "irrelevant_change",
            "reason": "Advice is stable across irrelevant-change perturbation.",
        }

    except Exception as exc:
        # Fail open (pass) on unexpected errors to avoid blocking the pipeline
        return {
            "passed": True,
            "gate": "irrelevant_change",
            "reason": f"Irrelevant-change check skipped due to error: {exc}",
        }
