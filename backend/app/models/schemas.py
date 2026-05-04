from pydantic import BaseModel
from typing import Literal, Optional


class AnalyseRequest(BaseModel):
    github_url: str


# ── Agent step events streamed to the frontend ──────────────────────────────

class StepEvent(BaseModel):
    """One reasoning step emitted by the agent pipeline."""
    step: Literal[
        "classify",
        "obligations",
        "evidence",
        "report",
        "error",
    ]
    status: Literal["start", "done", "stream"]
    payload: dict  # free-form, step-specific content


# ── Obligation schema ────────────────────────────────────────────────────────

class Obligation(BaseModel):
    id: str
    tenet: str
    article: str
    applies_if: str
    signals_to_check: list[str]
    not_checkable_in_code: list[str]
    confidence_ceiling: float  # 0.0–1.0 max achievable score from code alone


# ── Evidence gathered per signal ────────────────────────────────────────────

class SignalEvidence(BaseModel):
    signal: str
    found: bool
    locations: list[str]   # file paths or search snippets
    note: str


class ObligationEvidence(BaseModel):
    obligation_id: str
    signal_results: list[SignalEvidence]


# ── Final compliance finding per obligation ──────────────────────────────────

class ComplianceFinding(BaseModel):
    obligation_id: str
    tenet: str
    article: str
    score: float            # 0.0–1.0 actual score
    confidence: float       # how confident we are in that score
    confidence_ceiling: float
    verdict: Literal["compliant", "partial", "non-compliant", "not-checkable"]
    summary: str
    evidence_highlights: list[str]
    not_checkable_notes: list[str]


# ── Top-level report ─────────────────────────────────────────────────────────

class ComplianceReport(BaseModel):
    repo_url: str
    repo_name: str
    risk_tier: Literal["unacceptable", "high", "limited", "minimal"]
    risk_tier_reasoning: str
    overall_score: float
    overall_confidence: float
    findings: list[ComplianceFinding]
