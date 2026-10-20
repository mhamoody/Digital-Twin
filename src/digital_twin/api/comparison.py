"""Fail-closed temporal comparison for declared course checkpoints."""

from .schemas import TemporalComparison

DEFAULT_CHECKPOINTS = {"oulad:AAA:2013J": (3, 5, 8, 10)}


def compare_predictions(enrolment, state, current, states_by_week, predictions_by_state, schedule):
    result = TemporalComparison(current_checkpoint=state.checkpoint_week if state else None)

    def unavailable(reason):
        return result.model_copy(update={"reason": reason})

    if state is None or current is None:
        return unavailable("NO_CURRENT_PREDICTION")
    if not schedule or state.checkpoint_week not in schedule:
        return unavailable("CHECKPOINT_POLICY_UNAVAILABLE")
    if enrolment.registration_day is None:
        return unavailable("ELIGIBILITY_UNKNOWN")
    eligible = [week for week in schedule if enrolment.registration_day <= week * 7 - 1 and
                (enrolment.unregistration_day is None or enrolment.unregistration_day > week * 7 - 1)]
    if state.checkpoint_week not in eligible:
        return unavailable("INELIGIBLE_CHECKPOINT")
    earlier = [week for week in eligible if week < state.checkpoint_week]
    if not earlier:
        return unavailable("NO_PREVIOUS_CHECKPOINT")
    previous_checkpoint = max(earlier)
    result = result.model_copy(update={"previous_checkpoint": previous_checkpoint})
    previous_state = states_by_week.get(previous_checkpoint)
    previous = predictions_by_state.get(previous_state.state_id) if previous_state else None
    if previous is None:
        return unavailable("NO_PREVIOUS_PREDICTION")
    now, model = current
    before, previous_model = previous
    if now.state_id != state.state_id or before.state_id != previous_state.state_id:
        return unavailable("STATE_MISMATCH")
    if now.abstain or before.abstain:
        return unavailable("ABSTAINED")
    if not now.quality_gate_passed or not before.quality_gate_passed:
        return unavailable("QUALITY_GATE_FAILED")
    if state.data_origin != previous_state.data_origin or state.feature_set_version != previous_state.feature_set_version:
        return unavailable("ORIGIN_MISMATCH" if state.data_origin != previous_state.data_origin else "FEATURE_VERSION_MISMATCH")
    if model.model_ref != previous_model.model_ref:
        return unavailable("MODEL_MISMATCH")
    if now.calibration_version != before.calibration_version:
        return unavailable("CALIBRATION_MISMATCH")
    if not now.calibration_version or now.calibration_version == "identity-demo-v1" or model.model_kind == "simple_demo":
        return unavailable("UNCALIBRATED")
    if now.display_probability is None or before.display_probability is None:
        return unavailable("NO_DISPLAY_PROBABILITY")
    return result.model_copy(update={"available": True, "reason": None,
        "previous_value": before.display_probability, "current_value": now.display_probability,
        "delta": now.display_probability - before.display_probability})
