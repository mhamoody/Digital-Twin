from src.llm.service import generate_llm_risk_summary

sample_state = {
    "week": 5,
    "engagement_score": 0.31,
    "active_days": 1,
    "missed_assessments": 1,
    "activity_trend": "declining",
    "evidence_ids": ["ev12", "ev18"]
}

result = generate_llm_risk_summary(sample_state, model_name="qwen2.5:7b")
print(result)