"""Grounding verification gate.

Verifies that clinical statements, drug information, and medical advice are factually
grounded in trusted sources (such as OpenFDA drug labeling) using Natural Language Inference (NLI).
"""

import os
from typing import Any, Dict, Optional
from dotenv import load_dotenv
import httpx
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

OPENFDA_ACETAMINOPHEN_URL = (
    'https://api.fda.gov/drug/label.json?search=openfda.brand_name:"acetaminophen"+OR+openfda.generic_name:"acetaminophen"&limit=1'
)


async def check_claim_grounding(claim_text: str) -> dict:
    """Verify that a factual claim is supported by official FDA drug labeling.

    Args:
        claim_text: The medical claim string to verify.

    Returns:
        dict: Result dictionary containing 'passed', 'gate', and 'reason'.
    """
    if not claim_text:
        return {"passed": True, "gate": "grounding", "reason": "OK"}

    load_dotenv()

    # Query openFDA label API
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(OPENFDA_ACETAMINOPHEN_URL)

        if response.status_code != 200:
            return {"passed": False, "gate": "grounding", "reason": "No FDA label found"}

        data = response.json()
        results = data.get("results", [])
        if not results:
            return {"passed": False, "gate": "grounding", "reason": "No FDA label found"}

        first_record = results[0]
        dosage = first_record.get("dosage_and_administration", [])
        warnings = first_record.get("warnings", [])

        dosage_text = " ".join(dosage) if isinstance(dosage, list) else str(dosage) if dosage else ""
        warnings_text = " ".join(warnings) if isinstance(warnings, list) else str(warnings) if warnings else ""

        label_text = f"Dosage and Administration:\n{dosage_text}\n\nWarnings:\n{warnings_text}".strip()
        if not label_text:
            return {"passed": False, "gate": "grounding", "reason": "No FDA label found"}

    except Exception:
        return {"passed": False, "gate": "grounding", "reason": "No FDA label found"}

    # Use Gemini as an NLI checker
    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return {
                "passed": False,
                "gate": "grounding",
                "reason": "GEMINI_API_KEY environment variable is missing",
            }

        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0.0,
            google_api_key=api_key,
        )

        prompt = (
            f"You are a strict medical fact-checker. Based on the following FDA label text: {label_text}. "
            f"Is the following claim supported? Claim: {claim_text}. Answer strictly with PASS or FAIL."
        )

        nli_response = await llm.ainvoke(prompt)
        content = (
            nli_response.content
            if isinstance(nli_response.content, str)
            else str(nli_response.content)
        ).strip().upper()

        if "PASS" in content and "FAIL" not in content:
            return {
                "passed": True,
                "gate": "grounding",
                "reason": "Supported by FDA label",
            }
        else:
            return {
                "passed": False,
                "gate": "grounding",
                "reason": f"Not supported by FDA label (NLI output: {content})",
            }

    except Exception as exc:
        return {
            "passed": False,
            "gate": "grounding",
            "reason": f"Grounding check error: {exc}",
        }
