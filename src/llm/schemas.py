from pydantic import BaseModel
from typing import List

class Claim(BaseModel):
    claim_code: str
    evidence_id: str

class RiskOutput(BaseModel):
    risk_level: str
    risk_score: float
    claims: List[Claim]
    recommended_actions: List[str]
    abstain: bool