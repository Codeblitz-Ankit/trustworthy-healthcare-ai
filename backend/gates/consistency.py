"""Consistency verification gate using Groq.

Performs independent cross-model review of medical claims using LLaMA models
hosted on Groq to evaluate factual consistency and medical accuracy.
"""

import os
from typing import Any, Dict
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

    try:
        llm = ChatGroq(
            model="llama-3.1-8b-instant",
            temperature=0.0,
            groq_api_key=groq_api_key,
        )

        prompt = (
            f"You are an independent medical reviewer. Evaluate this claim for factual consistency "
            f"and standard medical accuracy. Claim: {claim_text}. If the claim is safe and accurate, "
            f"output exactly PASS. If it is factually wrong or dangerous, output FAIL."
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

    except Exception:
        return {
            "passed": False,
            "gate": "consistency",
            "reason": "Failed independent Groq review",
        }
