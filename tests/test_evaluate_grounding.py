import json
from pathlib import Path
from scripts.evaluate_grounding import protocol, PROTOCOL_SHA, LEGACY_WINDOWS_CRLF_SHA, run_case, model_visible_case
import hashlib
from digital_twin.evaluation.research_adapter import ResearchRuntime

def test_runner_verifies_frozen_protocol():
    doc, digest = protocol(Path("evaluation/protocols/e2_grounding_heldout_v1.json"))
    assert digest == PROTOCOL_SHA and len(doc["cases"]) == 48

def test_lf_and_crlf_have_same_canonical_hash_and_content():
    raw = Path("evaluation/protocols/e2_grounding_heldout_v1.json").read_bytes()
    lf = raw.decode().replace("\r\n", "\n").replace("\r", "\n").encode()
    crlf = lf.replace(b"\n", b"\r\n")
    assert hashlib.sha256(lf).hexdigest().upper() == PROTOCOL_SHA
    assert hashlib.sha256(crlf).hexdigest().upper() == LEGACY_WINDOWS_CRLF_SHA
    assert json.loads(lf) == json.loads(crlf)

def test_canonical_hash_changes_for_content_modification():
    raw = Path("evaluation/protocols/e2_grounding_heldout_v1.json").read_bytes()
    canonical = raw.decode().replace("\r\n", "\n").replace("\r", "\n").encode()
    changed = canonical.replace(b'"checkpoint":  3', b'"checkpoint":  4', 1)
    assert hashlib.sha256(changed).hexdigest().upper() != PROTOCOL_SHA

def test_runner_variant_schema_separation():
    class Fake:
        runtime=ResearchRuntime("http://127.0.0.1:11434","qwen2.5:7b",{"temperature":0.0,"seed":42,"num_ctx":8192,"num_predict":1200})
        def generate(self, case, **kwargs):
            assert kwargs.get("schema") is None
            return {"parsed":{"assessment":"ok","claims":[],"abstain":True},"metadata":{"latency_ms":1}}
    case={"case_id":"x","scenario_family":"f","checkpoint":3,"course_policy":"weekly_participation","permitted_evidence":[],"_variant":"plain_llm"}
    row=run_case(Fake(),case,"plain_llm","d","r","c","p")
    assert row["abstained"] is True and row["accepted"] is False

def test_model_visible_projection_excludes_reference_fields():
    case={"case_id":"x","scenario_family":"genuine_inactivity","checkpoint":3,"course_policy":"weekly_participation","permitted_evidence":["activity"],"expected_behavior_class":"assessment_allowed","expected_evidence_constraints":["no_causal_claim"]}
    visible=model_visible_case(case)
    assert set(visible)=={"checkpoint","course_policy","permitted_evidence"}
    assert all(key not in json.dumps(visible) for key in ("case_id","scenario_family","expected_behavior_class","expected_evidence_constraints"))

def test_v2_protocol_shape_and_balanced_reference_labels():
    doc=json.loads(Path("evaluation/protocols/e2_grounding_heldout_v2.json").read_text(encoding="utf-8"))
    assert doc["protocol_version"]=="v2" and len(doc["cases"])==48
    assert len({c["scenario_family"] for c in doc["cases"]})==12
    assert {f:sum(c["scenario_family"]==f for c in doc["cases"]) for f in {c["scenario_family"] for c in doc["cases"]}} == {f:4 for f in {c["scenario_family"] for c in doc["cases"]}}
    assert sum(c["evaluation_reference"]["expected_behavior_class"]=="assessment_allowed" for c in doc["cases"])==24
    assert len({json.dumps(c["model_input"],sort_keys=True) for c in doc["cases"]})==48

def test_v2_manifest_hash_matches_runner_constant():
    import hashlib
    from scripts.evaluate_grounding import V2_PROTOCOL_SHA
    raw=Path("evaluation/protocols/e2_grounding_heldout_v2.json").read_bytes()
    canonical=raw.decode("utf-8-sig").replace("\r\n","\n").replace("\r","\n").encode()
    manifest=json.loads(Path("evaluation/protocols/e2_grounding_heldout_v2_manifest.json").read_text(encoding="utf-8-sig"))
    assert hashlib.sha256(canonical).hexdigest().upper()==manifest["canonical_sha256"]==V2_PROTOCOL_SHA


