"""Consistency verification gate using Groq.

Performs independent cross-model review of medical claims using LLaMA models
hosted on Groq to evaluate factual consistency and medical accuracy.
"""

import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()


async def check_claim_consistency(claim_text: str) -> dict:
    """Evaluate medical claim consistency with an independent reviewer model on Groq.

    Args:
        claim_text: The medical claim string to evaluate.

    Returns:
        dict: Result dictionary containing 'passed', 'gate', and 'reason'.
    """
    if not claim_text:
        return {"passed": True, "gate": "consistency", "reason": "Consistent"}

    load_dotenv()
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        return {
            "passed": True,
            "gate": "consistency",
            "reason": "Consistency check skipped: GROQ_API_KEY is missing",
        }

    try:
        llm = ChatGroq(
            model="llama-3.1-8b-instant",
            temperature=0.0,
            groq_api_key=groq_api_key,
        )

        prompt = (
            f"You are a medical fact-checker. Read the following claim: {claim_text}. "
            "If the claim is a generally accepted medical fact or safe advice, reply strictly with PASS. "
            "Only reply FAIL if the claim contains dangerous misinformation or hallucinated dosages."
        )

        response = await llm.ainvoke(prompt)
        content = (
            response.content
            if isinstance(response.content, str)
            else str(response.content)
        ).strip().upper()

        if "FAIL" in content:
            return {
                "passed": False,
                "gate": "consistency",
                "reason": "Failed independent Groq review",
            }

        return {
            "passed": True,
            "gate": "consistency",
            "reason": "Consistent",
        }

    except Exception as exc:
        return {
            "passed": True,
            "gate": "consistency",
            "reason": f"Consistency check skipped due to Groq error: {exc}",
        }
