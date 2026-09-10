from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional

from src.llm.service import generate_llm_risk_summary

app = FastAPI(title="Digital Twin LLM Integration API")

class WeeklyStateRequest(BaseModel):
    week: int
    engagement_score: Optional[float] = None
    active_days: Optional[int] = None
    missed_assessments: Optional[int] = None
    activity_trend: Optional[str] = None
    evidence_ids: List[str] = []

class LLMRequest(BaseModel):
    model_name: str = "qwen2.5:7b"
    state: WeeklyStateRequest

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/llm/evaluate")
def llm_evaluate(req: LLMRequest):
    result = generate_llm_risk_summary(
        state=req.state.model_dump(),
        model_name=req.model_name
    )
    return result