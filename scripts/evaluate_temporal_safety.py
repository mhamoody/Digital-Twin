from __future__ import annotations
import argparse,json,csv
from pathlib import Path
from digital_twin.evaluation.canonical import export_temporal_records
from digital_twin.evaluation.temporal import cutoff_violations

def main():
 p=argparse.ArgumentParser();p.add_argument("--states",required=True);p.add_argument("--output",default="evaluation/results/e4_temporal_v1.csv");a=p.parse_args();data=json.loads(Path(a.states).read_text(encoding="utf-8"));records=export_temporal_records(data);violations=cutoff_violations([{**r,"features":[{"source_time":r["source_time"],"source":r["feature_source"]}]} for r in records if r["source_time"] is not None]);Path(a.output).parent.mkdir(parents=True,exist_ok=True)
 with open(a.output,"w",newline="",encoding="utf-8") as h:
  w=csv.DictWriter(h,fieldnames=list(records[0]) if records else ["learner_id","presentation_id","checkpoint","checkpoint_time","feature_source","source_time"]);w.writeheader();w.writerows(records)
 print(json.dumps({"status":"E4 TEMPORAL SAFETY = COMPLETED" if not violations else "E4 TEMPORAL SAFETY = FAILED","learners_audited":len({r["learner_id"] for r in records}),"checkpoints_audited":len({r["checkpoint"] for r in records}),"feature_records":len(records),"violations":len(violations)},indent=2))
if __name__=="__main__":main()
