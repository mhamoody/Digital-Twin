from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import time

router = APIRouter(prefix="/api/v1/llm", tags=["llm"])

class StateIn(BaseModel):
    week: int
    engagement_score: float
    active_days: int
    missed_assessments: int
    activity_trend: str
    evidence_ids: List[str]

class EvalRequest(BaseModel):
    model_name: str
    state: StateIn

@router.post("/evaluate")
def evaluate(req: EvalRequest):
    t0 = time.time()
    return {
        "model": req.model_name,
        "json_valid": True,
        "schema_valid": True,
        "latency_sec": round(time.time() - t0, 3),
        "data": {
            "risk_level": "medium",
            "risk_score": 0.58,
            "claims": [],
            "recommended_actions": [],
            "abstain": False
        },
        "error": None
    }
