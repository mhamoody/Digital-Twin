import json
from pydantic import ValidationError
from src.llm.schemas import RiskOutput

def clean_markdown(text: str) -> str:
    return text.replace("```json", "").replace("```", "").strip()

def validate_output(raw_text: str):
    cleaned = clean_markdown(raw_text)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        return {
            "json_valid": False,
            "schema_valid": False,
            "data": None,
            "error": f"Invalid JSON: {str(e)}"
        }

    try:
        validated = RiskOutput(**parsed)
        return {
            "json_valid": True,
            "schema_valid": True,
            "data": validated.model_dump(),
            "error": None
        }
    except ValidationError as e:
        return {
            "json_valid": True,
            "schema_valid": False,
            "data": None,
            "error": f"Schema validation failed: {str(e)}"
        }