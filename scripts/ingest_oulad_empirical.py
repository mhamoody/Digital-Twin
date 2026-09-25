"""Ingest a prepared empirical OULAD presentation into the canonical store."""
from __future__ import annotations
import argparse, csv, hashlib, json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session

from digital_twin.alerts import create_demo_alert
from digital_twin.models import predict_demo_risk
from digital_twin.persistence import TwinStore, create_twin_engine
from digital_twin.persistence.store import stable_hash
from digital_twin.persistence.models import CoursePresentation, Enrolment, SourceObservation
from digital_twin.schemas import DataOrigin
from digital_twin.state import build_weekly_states

REQUIRED = ("course_presentations.csv","enrolments.csv","resources.csv","assessments.csv",
            "assessment_observations.csv","activity_observations.csv","manifest.json")
CHECKPOINTS = (3, 5, 8, 10)

def validate_prepared(directory: Path) -> dict:
    manifest_path = directory / "manifest.json"
    if not manifest_path.is_file(): raise ValueError("manifest.json is required")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    module = manifest.get("module")
    presentation = manifest.get("presentation")
    expected_id = f"oulad:{module}:{presentation}"
    if not module or not presentation or manifest.get("presentation_id") != expected_id:
        raise ValueError("prepared dataset has invalid presentation identity")
    if manifest.get("data_origin") != "empirical":
        raise ValueError("prepared dataset has invalid presentation or origin")
    for name, info in manifest.get("outputs", {}).items():
        path = directory / name
        if not path.is_file(): raise ValueError(f"missing prepared artifact: {name}")
        if info.get("sha256") and hashlib.sha256(path.read_bytes()).hexdigest() != info["sha256"]:
            raise ValueError(f"artifact hash mismatch: {name}")
    for name in REQUIRED:
        if not (directory / name).is_file(): raise ValueError(f"missing prepared artifact: {name}")
    return manifest

def rows(path: Path):
    with path.open(encoding="utf-8", newline="") as h: yield from csv.DictReader(h)

def ingest(database_url: str, prepared_dir: Path) -> dict:
    manifest = validate_prepared(prepared_dir)
    now = datetime.now(UTC)
    engine = create_twin_engine(database_url)
    presentation = next(rows(prepared_dir / "course_presentations.csv"))
    if presentation["presentation_id"] != manifest["presentation_id"]:
        raise ValueError("course presentation does not match manifest")
    if presentation["module_code"] != manifest["module"] or presentation["presentation_code"] != manifest["presentation"]:
        raise ValueError("course presentation codes do not match manifest")
    enrolments = list(rows(prepared_dir / "enrolments.csv"))
    source_id = manifest["source_id"]
    observations = []
    for r in enrolments:
        observations.append({"observation_id": r["source_record_id"], "presentation_id": r["presentation_id"], "learner_id": r["learner_id"], "observation_kind":"enrolment", "source_record_id":r["source_record_id"], "course_day":int(r["registration_day"] or 0), "event_code":"course_enrolled", "event_at":None,"available_at":None,"time_precision":"relative_day","value":True,"count":None,"adapter_version":"oulad-empirical-v1","metadata":{},"data_origin":"empirical"})
    for r in rows(prepared_dir / "activity_observations.csv"):
        observations.append({"observation_id":r["source_record_id"],"presentation_id":r["presentation_id"],"learner_id":r["learner_id"],"observation_kind":"activity","source_record_id":r["source_record_id"],"course_day":int(r["course_day"]),"event_code":f"activity_{r['activity_group']}","event_at":None,"available_at":None,"time_precision":"relative_day","value":None,"count":int(r["click_count"]),"adapter_version":"oulad-empirical-v1","metadata":{"resource_id":r["resource_id"]},"data_origin":"empirical"})
    for r in rows(prepared_dir / "assessment_observations.csv"):
        observations.append({"observation_id":r["source_record_id"],"presentation_id":r["presentation_id"],"learner_id":r["learner_id"],"observation_kind":"assessment","source_record_id":r["source_record_id"],"course_day":int(r["submitted_course_day"]),"event_code":"assessment_submitted","event_at":None,"available_at":None,"time_precision":"relative_day","value":float(r["score"]) if r["score"] else None,"count":1,"adapter_version":"oulad-empirical-v1","metadata":{"assessment_id":r["assessment_id"],"score_missing_reason":r["score_missing_reason"]},"data_origin":"empirical"})
    for r in rows(prepared_dir / "assessments.csv"):
        if not r["due_course_day"]: continue
        observations.append({"observation_id":f"assessment-def:{r['source_assessment_id']}","presentation_id":r["presentation_id"],"learner_id":None,"observation_kind":"assessment_definition","source_record_id":f"assessment-def:{r['source_assessment_id']}","course_day":int(r["due_course_day"]),"event_code":"assessment_due","event_at":None,"available_at":None,"time_precision":"relative_day","value":float(r["weight"]),"count":1,"adapter_version":"oulad-empirical-v1","metadata":{"assessment_id":r["assessment_id"]},"data_origin":"empirical"})
    run_key=stable_hash({"manifest":manifest["outputs"],"presentation":manifest["presentation_id"]}); run_id=f"run:oulad:empirical:{run_key[:20]}"
    store=TwinStore(engine); store.register_source(source_id=source_id,name="OULAD",version="2015-release",licence_note="Open University Learning Analytics Dataset",manifest_hash=stable_hash(manifest),imported_at=now); store.begin_run(run_id=run_id,source_id=source_id,idempotency_key=run_key,started_at=now,adapter_version="oulad-empirical-v1",schema_version="canonical-observation-v1")
    core=store.persist_prepared_core(run_id=run_id,presentation={"presentation_id":manifest["presentation_id"],"source_id":source_id,"module_code":presentation["module_code"],"presentation_code":presentation["presentation_code"],"length_days":int(presentation["length_days"]),"data_origin":"empirical"},enrolments=enrolments,observations=observations)
    activities=[{"learner_id":r["learner_id"],"course_day":r["course_day"],"click_count":r["click_count"],"activity_group":r["activity_group"],"source_record_id":r["source_record_id"]} for r in rows(prepared_dir/"activity_observations.csv")]
    assessments=[dict(r, presentation_id=manifest["presentation_id"], source_record_id=f"assessment-def:{r['source_assessment_id']}") for r in rows(prepared_dir/"assessments.csv")]
    assobs=[dict(r) for r in rows(prepared_dir/"assessment_observations.csv")]
    builder_enrolments=[dict(r) for r in enrolments]
    states=build_weekly_states(enrolments=builder_enrolments,activities=activities,assessments=assessments,assessment_observations=assobs,checkpoints=CHECKPOINTS,built_at=now,data_origin=DataOrigin.EMPIRICAL,feature_set_version="oulad-demo-features-v1",is_fresh=True)
    predictions=[predict_demo_risk(s,now) for s in states]; alerts=[a for s,p in zip(states,predictions,strict=True) if (a:=create_demo_alert(p,is_fresh=s.is_fresh,created_at=now))]
    analytics=store.persist_analytics(run_id=run_id,states=states,predictions=predictions,alerts=alerts,occurred_at=now); store.accept_run(run_id=run_id,accepted_at=now,counts={"states":len(states),"predictions":len(predictions),"alerts":len(alerts)})
    return {"core":core.inserted,"analytics":analytics.inserted,"states":len(states),"predictions":len(predictions),"alerts":len(alerts),"presentation_id":manifest["presentation_id"]}

def main():
    p=argparse.ArgumentParser(); p.add_argument("--database-url",required=True); p.add_argument("--prepared-dir",type=Path,required=True); a=p.parse_args(); print(json.dumps(ingest(a.database_url,a.prepared_dir),indent=2)); return 0
if __name__ == "__main__": raise SystemExit(main())
