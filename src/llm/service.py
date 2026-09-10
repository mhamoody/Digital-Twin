from src.llm.prompt_builder import build_risk_prompt
from src.llm.ollama_client import call_ollama
from src.llm.validator import validate_output

def generate_llm_risk_summary(state: dict, model_name: str = "qwen2.5:7b"):
    prompt = build_risk_prompt(state)
    raw_text, latency = call_ollama(prompt=prompt, model_name=model_name)
    validation = validate_output(raw_text)

    return {
        "model": model_name,
        "latency_sec": latency,
        "raw_output": raw_text,
        "json_valid": validation["json_valid"],
        "schema_valid": validation["schema_valid"],
        "data": validation["data"],
        "error": validation["error"]
    }