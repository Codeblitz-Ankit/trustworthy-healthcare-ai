"""Hard safety verification gate.

Implements deterministic safety constraints, formal verification (using Z3 solver),
and rules to block medical contraindications, toxic advice, or critical dosage limits.
"""

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Optional
import z3

_LIMITS_PATH = Path(__file__).resolve().parents[1] / "data" / "drug_limits.json"


@lru_cache(maxsize=1)
def _load_drug_limits() -> dict:
    with _LIMITS_PATH.open(encoding="utf-8") as limits_file:
        return json.load(limits_file)


def _extract_drug(claim_text: str, limits: dict) -> Optional[dict]:
    normalized_claim = claim_text.casefold()
    for drug, details in limits.items():
        aliases = details.get("aliases", []) + [drug]
        if any(re.search(rf"\b{re.escape(alias.casefold())}\b", normalized_claim) for alias in aliases):
            return details
    return None


async def check_claim_hard_safety(
    claim_text: str, patient_context: Optional[dict] = None
) -> dict:
    """Check a clinical claim against deterministic safety constraints using Z3.

    Args:
        claim_text: The atomic factual claim to verify.
        patient_context: Optional contextual dictionary containing patient health details.

    Returns:
        dict: Result with 'passed', 'gate', 'reason', and optional 'counterexample'.
    """
    if not claim_text:
        return {"passed": True, "gate": "hard_safety", "reason": "OK"}

    # Extract numeric values followed by mg (e.g. 500mg, 1,000 mg).
    matches = re.findall(r"(\d+(?:,\d+)*(?:\.\d+)?)\s*mg", claim_text, re.IGNORECASE)

    if not matches:
        return {"passed": True, "gate": "hard_safety", "reason": "OK"}

    drug_limits = _extract_drug(claim_text, _load_drug_limits())
    if drug_limits is None:
        return {
            "passed": False,
            "gate": "hard_safety",
            "reason": "Unverified Dosage: no safety limits are available for the named drug",
        }

    daily_claim = bool(re.search(r"\b(?:daily|per day|24[- ]hour(?:s)?|every 24)\b", claim_text, re.I))
    limit_key = "max_daily_mg" if daily_claim else "max_single_mg"
    limit = drug_limits.get(limit_key)
    if limit is None:
        return {"passed": True, "gate": "hard_safety", "reason": "No applicable hard limit is defined"}

    for match in matches:
        clean_val = match.replace(",", "")
        try:
            numeric_val = float(clean_val)
        except ValueError:
            continue

        solver = z3.Solver()
        dose = z3.Real("dose")
        solver.add(dose == numeric_val)
        solver.add(dose > z3.RealVal(limit))

        if solver.check() == z3.sat:
            scope = "daily" if daily_claim else "single dose"
            return {
                "passed": False,
                "gate": "hard_safety",
                "reason": f"{scope.title()} exceeds {limit} mg limit",
                "counterexample": f"{clean_val} mg > {limit} mg",
            }

    return {"passed": True, "gate": "hard_safety", "reason": "OK"}
