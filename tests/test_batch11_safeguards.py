from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from digital_twin.api.auth import _development_grants, authorize_course
from digital_twin.api.comparison import compare_predictions
from digital_twin.api.schemas import InstructorIdentity
from digital_twin.api.service import select_bound_prediction


def state(week, state_id=None):
    return SimpleNamespace(state_id=state_id or f"s{week}", checkpoint_week=week,
                           learner_id="l1", presentation_id="oulad:AAA:2013J",
                           data_origin="empirical", feature_set_version="v1")


def prediction(s, model="m1", calibration="cal-v1", value=.5):
    return (SimpleNamespace(state_id=s.state_id, abstain=False, quality_gate_passed=True,
                            calibration_version=calibration, display_probability=value),
            SimpleNamespace(model_ref=model, model_kind="logistic"))


def test_prediction_binding_never_uses_older_state():
    old, current = state(8), state(10)
    assert select_bound_prediction(current, [prediction(old)]) is None
    assert select_bound_prediction(current, [prediction(old), prediction(current)]) is not None


@pytest.mark.parametrize("mode,reason", [("missing", "NO_PREVIOUS_PREDICTION"),
                                           ("model", "MODEL_MISMATCH"),
                                           ("cal", "CALIBRATION_MISMATCH"),
                                           ("uncal", "UNCALIBRATED")])
def test_temporal_comparison_is_immediate_and_fail_closed(mode, reason):
    enrolment = SimpleNamespace(registration_day=0, unregistration_day=None)
    s3, s5, s8, s10 = [state(w) for w in (3, 5, 8, 10)]
    current = prediction(s10, calibration="identity-demo-v1" if mode == "uncal" else "cal-v1")
    previous = None if mode == "missing" else prediction(
        s8, model="other" if mode == "model" else "m1",
        calibration=("other-cal" if mode == "cal" else
                     "identity-demo-v1" if mode == "uncal" else "cal-v1"))
    result = compare_predictions(enrolment, s10, current,
                                 {3: s3, 5: s5, 8: s8, 10: s10},
                                 {s8.state_id: previous} if previous else {},
                                 (3, 5, 8, 10))
    assert not result.available and result.previous_checkpoint == 8
    assert result.reason == reason


def test_missing_immediate_checkpoint_does_not_fall_back():
    enrolment = SimpleNamespace(registration_day=0, unregistration_day=None)
    s5, s10 = state(5), state(10)
    result = compare_predictions(enrolment, s10, prediction(s10), {5: s5, 10: s10},
                                 {s5.state_id: prediction(s5)}, (3, 5, 8, 10))
    assert not result.available and result.reason == "NO_PREVIOUS_PREDICTION"


def test_course_grants_fail_closed(monkeypatch):
    identity = InstructorIdentity(reviewer_id="instructor:test", role="instructor",
                                  allowed_presentations=["oulad:AAA:2013J"])
    authorize_course(identity, "oulad:AAA:2013J")
    with pytest.raises(HTTPException):
        authorize_course(identity, "other")
    monkeypatch.delenv("DIGITAL_TWIN_DEVELOPMENT_AUTH", raising=False)
    assert _development_grants("instructor:test") == []
    monkeypatch.setenv("DIGITAL_TWIN_DEVELOPMENT_AUTH", "1")
    monkeypatch.setenv("DIGITAL_TWIN_COURSE_GRANTS_FILE", "missing-grants-file.json")
    assert _development_grants("instructor:test") == []
