import json
from pathlib import Path
from scripts.evaluate_grounding import protocol, PROTOCOL_SHA, run_case
from digital_twin.evaluation.research_adapter import ResearchRuntime

def test_runner_verifies_frozen_protocol():
    doc, digest = protocol(Path("evaluation/protocols/e2_grounding_heldout_v1.json"))
    assert digest == PROTOCOL_SHA and len(doc["cases"]) == 48

def test_runner_variant_schema_separation():
    class Fake:
        runtime=ResearchRuntime("http://127.0.0.1:11434","qwen2.5:7b",{"temperature":0.0,"seed":42,"num_ctx":8192,"num_predict":1200})
        def generate(self, case, **kwargs):
            assert kwargs.get("schema") is None
            return {"parsed":{"assessment":"ok","claims":[],"abstain":True},"metadata":{"latency_ms":1}}
    case={"case_id":"x","scenario_family":"f","checkpoint":3,"permitted_evidence":[],"_variant":"plain_llm"}
    row=run_case(Fake(),case,"plain_llm","d","r","c","p")
    assert row["abstained"] is True and row["accepted"] is False


