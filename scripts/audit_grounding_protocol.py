from __future__ import annotations
import argparse,json,sys
from collections import Counter
from pathlib import Path
def audit(path):
 d=json.loads(Path(path).read_text(encoding="utf-8")); cases=d.get("cases",[]); errors=[]; fam=Counter(c.get("scenario_family") for c in cases); labels=Counter(c.get("evaluation_reference",{}).get("expected_behavior_class") for c in cases)
 if d.get("protocol_version")!="v2" or len(cases)!=48: errors.append("version/case_count")
 if len(fam)!=12 or set(fam.values())!={4}: errors.append("family_distribution")
 if labels!={"assessment_allowed":24,"abstention_expected":24}: errors.append("behavior_distribution")
 vis=[]
 for c in cases:
  mi=c.get("model_input",{}); cp=mi.get("checkpoint",{}).get("timestamp","")
  if set(mi)!={"checkpoint","course_policy","evidence"}: errors.append("model_input_shape")
  if any(k in json.dumps(mi) for k in ("case_id","scenario_family","expected_behavior_class","expected_evidence_constraints","evaluation_reference")): errors.append("leakage")
  local=set()
  for e in mi.get("evidence",[]):
   if e.get("evidence_id") in local: errors.append("duplicate_evidence_id")
   local.add(e.get("evidence_id"))
   if e.get("observed") and e.get("source_time") and e["source_time"]>cp: errors.append("future_observation")
   if "evidence_ids" in e: errors.append("singular_evidence_id")
  vis.append(json.dumps(mi,sort_keys=True))
 if len(set(vis))!=48: errors.append("duplicate_model_inputs")
 return {"protocol_version":d.get("protocol_version"),"case_count":len(cases),"scenario_families":dict(fam),"behavior_distribution":dict(labels),"unique_model_inputs":len(set(vis)),"errors":sorted(set(errors))}
if __name__=="__main__":
 p=argparse.ArgumentParser(); p.add_argument("protocol"); a=p.parse_args(); result=audit(a.protocol); print(json.dumps(result,indent=2)); sys.exit(1 if result["errors"] else 0)

