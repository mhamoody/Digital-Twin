from __future__ import annotations

def export_temporal_records(states):
    """Adapt persisted canonical state features without inventing provenance."""
    rows=[]
    for state in states:
        checkpoint=state.get("checkpoint") or state.get("checkpoint_week")
        cutoff=state.get("cutoff_course_day")
        for feature in state.get("features",[]):
            source_time=feature.get("source_time")
            if source_time is None and feature.get("observed_at") is not None: source_time=feature["observed_at"]
            rows.append({"learner_id":state.get("learner_id"),"presentation_id":state.get("presentation_id"),"checkpoint":checkpoint,"checkpoint_time":cutoff,"feature_source":feature.get("name"),"source_time":source_time})
    return rows
