# GAP ANALYSIS: MVP vs. SDP PPT Requirements

> **Project:** Trustworthy AI Agents for Safe and Reliable Healthcare Applications
> **PPT Source:** SDP_PPT_01_1.pdf – SDP Project Review 02
> **Auditor:** Senior Software Architect / QA Review
> **Date:** 2026-11-14

---

## 1. Functional Requirements

| Requirement (from PPT) | Implementation Status | Location |
|---|---|---|
| Split AI answer into verifiable claims | ✅ Implemented | `backend/graph/nodes.py` → `proposer_node` |
| Check every claim against safety rules | ✅ Implemented | `backend/gates/hard_safety.py` → Z3 dose check |
| Check every claim against approved medical sources | ✅ Implemented | `backend/gates/grounding.py` → openFDA NLI |
| Probe Consistency gate (cross-check claims) | ✅ Implemented | `backend/gates/consistency.py` → Groq LLaMA |
| Irrelevant-Change Test gate | ❌ **Missing** | No `irrelevant_change.py` gate exists |
| Three outcomes: Verified / Partially Verified / Not Verified | ✅ Implemented | `backend/graph/nodes.py` → `aggregator_node` |
| Clinician escalation for failed / high-risk cases | ⚠️ **Partial** – `review_required` flag exists but API does not return it; no UI banner. | Missing from `/verify` response and `ResultCard.jsx` |
| Controlled release: show only verified claims with sources | ✅ Implemented | `aggregator_node` + `ResultCard.jsx` |

---

## 2. Non-Functional Requirements

| Requirement (from PPT) | Implementation Status | Notes |
|---|---|---|
| Safety: 0 unverified claims released as advice | ✅ Implemented | All gates must pass; aggregator withholds on failure |
| Defaults to "not verified" within 1 second if check fails | ⚠️ **Partial** – No hard timeout enforced | No `asyncio.wait_for` timeout in pipeline |
| Performance: 95% low-risk responses within 5 s | ⚠️ **Not measured** | No latency tracking or logging |
| Performance: 95% high-risk responses within 30 s | ⚠️ **Not measured** | No latency tracking or logging |
| Privacy: patient data encrypted in transit (TLS 1.2+) | ⚠️ **Not configured** | Dev server runs plain HTTP; needs HTTPS termination |
| Privacy: patient data encrypted at rest (AES-256) | ⚠️ **Not configured** | No persistent data store in MVP |
| **100% of requests logged for audit** | ❌ **Missing** | No `audit.jsonl` or logging middleware |

---

## 3. Pipeline Architecture (How It Works)

| PPT-Defined Stage | Implementation Status | Location |
|---|---|---|
| **Input Safety Layer** – privacy, consent, injection filtering | ⚠️ **Partial** – Placeholder file exists with no logic; not wired into pipeline | `backend/security/input_safety.py` (empty) |
| **Main LLM Proposer** – draft answer + split into claims | ✅ Implemented | `backend/graph/nodes.py` → `proposer_node` using Gemini |
| **Gate 1: Hard Safety Rules** – dose limits, interactions, allergies | ✅ Implemented | `backend/gates/hard_safety.py` → Z3 formal solver |
| **Gate 2: Source Grounding** – guidelines, drug database | ✅ Implemented | `backend/gates/grounding.py` → openFDA + Gemini NLI |
| **Gate 3: Probe Consistency** – cross-check each claim | ✅ Implemented | `backend/gates/consistency.py` → Groq LLaMA-3.1-8B |
| **Gate 4: Irrelevant-Change Test** – answer must not change on irrelevant detail change | ❌ **Missing** | Does not exist |
| **LangGraph state machine orchestration** | ✅ Implemented | `backend/graph/pipeline.py` → 5-node `StateGraph` |
| **FastAPI REST backend** | ✅ Implemented | `backend/main.py` → `/verify` POST endpoint |
| **React frontend** | ✅ Implemented | `frontend/src/` → Vite + React 19 |
| **CORS for Vite dev server** | ✅ Implemented | `backend/main.py` → `CORSMiddleware` |

---

## 4. Technology Stack

| PPT-Specified Tool | Implemented | Notes |
|---|---|---|
| LLM: Gemini | ✅ | `langchain-google-genai` → `gemini-2.5-flash` |
| LLM: Llama (via Groq) | ✅ | `langchain-groq` → `llama-3.1-8b-instant` |
| Multi-agent checking: LangGraph | ✅ | `langgraph` → `StateGraph` |
| Backend: Python + FastAPI | ✅ | `fastapi` + `uvicorn` |
| Frontend: React | ✅ | Vite + React 19 |
| Formal verification: Z3 SMT solver | ✅ | `z3-solver` |
| Grounding: RAG / LangChain | ⚠️ **Partial** – LangChain used for LLM clients; no RAG retrieval layer | openFDA REST API used as source |
| Security: Docker / Kubernetes | ❌ **Not implemented** | Out of scope for MVP |

---

## 5. Priority Gaps to Address

| Priority | Gap | Action |
|---|---|---|
| 🔴 HIGH | **Gate 4 (Irrelevant-Change Test)** missing | Create `backend/gates/irrelevant_change.py` and wire into pipeline |
| 🔴 HIGH | **Input Safety Layer** – placeholder only, not wired | Implement `sanitize_input()` and add `input_safety_node` before `proposer` |
| 🔴 HIGH | **Audit logging** – 100% of requests must be logged | Add JSONL audit logger middleware to `backend/main.py` |
| 🟠 MEDIUM | **`review_required` not returned in API payload** | Update `/verify` to include `review_required` in JSON response |
| 🟠 MEDIUM | **Clinician escalation banner missing in UI** | Add banner to `ResultCard.jsx` when `review_required === true` |
| 🟡 LOW | **No latency enforcement / timeout** | Wrap pipeline invocation in `asyncio.wait_for` with 30 s timeout |
| 🟡 LOW | **No RAG retrieval layer** | openFDA REST is acceptable for MVP; note for future extension |

---

> The MVP correctly implements the core 3-gate pipeline and three-outcome aggregator. The critical
> missing pieces are: Gate 4 (Irrelevant-Change Test), Input Safety Layer logic,
> audit logging, and review_required exposure in the API and UI.
