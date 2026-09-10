import requests
import time

OLLAMA_URL = "http://localhost:11434/api/generate"

def call_ollama(prompt: str, model_name: str = "qwen2.5:7b", temperature: float = 0.2):
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature}
    }

    start = time.time()
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        latency = round(time.time() - start, 3)
        response.raise_for_status()
        raw_text = response.json().get("response", "")
        return raw_text, latency
    except Exception:
        # Fallback mock response if Ollama is unavailable
        mock = """
        {
          "risk_level": "moderate",
          "risk_score": 0.62,
          "claims": [
            {"claim_code": "LOW_ACTIVITY", "evidence_id": "ev12"},
            {"claim_code": "MISSED_WORK", "evidence_id": "ev18"}
          ],
          "recommended_actions": ["CHECK_IN", "REVIEW_ASSESSMENT"],
          "abstain": false
        }
        """
        latency = round(time.time() - start, 3)
        return mock, latency