import hashlib
import json
from pathlib import Path

import pytest
from datetime import UTC, datetime
from digital_twin.schemas import DataOrigin
from digital_twin.state import build_weekly_states

from scripts.ingest_oulad_empirical import REQUIRED, validate_prepared


def test_manifest_validation_accepts_verified_empirical_fixture(tmp_path: Path):
    target = tmp_path / "prepared"
    target.mkdir()

    outputs = {}
    for name in REQUIRED:
        if name == "manifest.json":
            continue
        payload = f"fixture:{name}\n".encode()
        (target / name).write_bytes(payload)
        outputs[name] = {"sha256": hashlib.sha256(payload).hexdigest()}

    manifest = {
        "module": "AAA",
        "presentation": "2013J",
        "presentation_id": "oulad:AAA:2013J",
        "data_origin": "empirical",
        "outputs": outputs,
    }
    (target / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    result = validate_prepared(target)

    assert result["presentation_id"] == "oulad:AAA:2013J"
    assert result["data_origin"] == "empirical"


def test_manifest_validation_rejects_replay_or_mismatch(tmp_path: Path):
    (tmp_path / "manifest.json").write_text(json.dumps({"module": "AAA", "presentation": "2013J", "presentation_id": "moodle-replay:AAA:2030A", "data_origin": "replayed", "outputs": {}}))
    with pytest.raises(ValueError, match="invalid presentation identity"):
        validate_prepared(tmp_path)


def test_manifest_validation_rejects_missing_artifact(tmp_path: Path):
    (tmp_path / "manifest.json").write_text(json.dumps({"module": "AAA", "presentation": "2013J", "presentation_id": "oulad:AAA:2013J", "data_origin": "empirical", "outputs": {}}))
    with pytest.raises(ValueError, match="missing prepared artifact"):
        validate_prepared(tmp_path)


def test_empirical_path_isolated_from_replay_and_research_models():
    source = Path(__file__).parents[1] / "scripts" / "ingest_oulad_empirical.py"
    text = source.read_text(encoding="utf-8")
    assert "moodle-replay" not in text
    assert "qwen" not in text.lower()
    assert "DataOrigin.EMPIRICAL" in text
    assert "prediction_state_id" not in text  # predictor contract binds state_id directly
    assert 'CHECKPOINTS = (3, 5, 8, 10)' in text


def test_weekly_builder_excludes_future_observation_at_checkpoint():
    enrolments = [{"presentation_id":"oulad:AAA:2013J", "learner_id":"oulad:1",
                   "registration_day":"0", "registration_missing_reason":"observed",
                   "unregistration_day":"", "unregistration_missing_reason":"not_applicable",
                   "previous_attempts":"0", "studied_credits":"60", "source_record_id":"enrolment:1"}]
    activities = [{"learner_id":"oulad:1", "course_day":"5", "click_count":"2",
                   "activity_group":"content", "source_record_id":"obs-before"},
                  {"learner_id":"oulad:1", "course_day":"30", "click_count":"99",
                   "activity_group":"content", "source_record_id":"obs-after"}]
    states = build_weekly_states(enrolments=enrolments, activities=activities,
        assessments=[], assessment_observations=[], checkpoints=(3, 5),
        built_at=datetime.now(UTC), data_origin=DataOrigin.EMPIRICAL,
        feature_set_version="oulad-demo-features-v1", is_fresh=True)
    early, late = states
    early_clicks = next(f.value for f in early.features if f.name == "clicks_cumulative")
    late_clicks = next(f.value for f in late.features if f.name == "clicks_cumulative")
    assert early_clicks == 2
    assert late_clicks == 101


def test_prediction_contract_binds_state_and_support_is_separate():
    source = Path(__file__).parents[1] / "scripts" / "ingest_oulad_empirical.py"
    text = source.read_text(encoding="utf-8")
    assert "predictions=[predict_demo_risk(s,now) for s in states]" in text
    assert "create_demo_alert" in text
    assert "SupportCase" not in text and "SupportAction" not in text
