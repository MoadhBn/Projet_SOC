"""Analysis API: single entry point of the AI engine.

Phase 3 skeleton: only the score is implemented. The anomaly score and the LLM
label are passed in by the caller until those parts of the engine exist.
"""
from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.scoring import Level, LlmLabel, compute_score, level_for, respond, respond_before_llm

app = FastAPI(title="SOC IA analysis API", version="0.1.0")


class ScoreRequest(BaseModel):
    rule_level: int = Field(ge=0, le=15, description="Wazuh rule level")
    misp_match: bool = Field(description="An indicator of the alert is known in MISP")
    anomaly_score: float = Field(ge=0.0, le=1.0, description="0 = normal, 1 = very unusual")
    llm_label: LlmLabel | None = None


class ScoreResponse(BaseModel):
    severity: float
    misp: float
    anomaly: float
    llm: float
    base_score: float
    final_score: float
    level: Level
    respond: bool
    respond_before_llm: bool


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/score")
def score(request: ScoreRequest) -> ScoreResponse:
    detail = compute_score(
        rule_level=request.rule_level,
        misp_match=request.misp_match,
        anomaly_score=request.anomaly_score,
        llm_label=request.llm_label,
    )
    return ScoreResponse(
        severity=round(detail.severity, 2),
        misp=round(detail.misp, 2),
        anomaly=round(detail.anomaly, 2),
        llm=round(detail.llm, 2),
        base_score=round(detail.base, 2),
        final_score=round(detail.total, 2),
        level=level_for(detail.total),
        respond=respond(detail),
        respond_before_llm=respond_before_llm(detail),
    )
