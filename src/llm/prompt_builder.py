import json

def build_risk_prompt(state: dict) -> str:
    return f"""
You are a constrained educational risk-analysis system.

Return STRICT valid JSON only.

Rules:
- Return exactly one JSON object.
- No markdown.
- No explanations.
- No extra fields.
- No missing fields.
- claims must contain:
  - claim_code
  - evidence_id
- Use only provided evidence IDs.
- If uncertain, set "abstain": true.

Approved claim codes:
- LOW_ACTIVITY
- MISSED_WORK
- DECLINING_TREND

Approved actions:
- CHECK_IN
- REVIEW_ASSESSMENT
- MONITOR_ACTIVITY

Input:
{json.dumps(state, indent=2)}

Required JSON schema:
{{
  "risk_level": "string",
  "risk_score": 0.0,
  "claims": [
    {{
      "claim_code": "LOW_ACTIVITY",
      "evidence_id": "ev12"
    }}
  ],
  "recommended_actions": [
    "CHECK_IN"
  ],
  "abstain": false
}}
"""