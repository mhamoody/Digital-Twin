from __future__ import annotations
import argparse,csv,json,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1])); sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from pathlib import Path
from scripts.evaluate_grounding import protocol, FIELDS, LEGACY_WINDOWS_CRLF_SHA
from digital_twin.evaluation.grounding_v2 import deterministic_output_validation, reference_scoring
from digital_twin.evaluation.e2_results import build_e2_summary, RESULT_FIELDS

def main():
 p=argparse.ArgumentParser(); p.add_argument('--protocol',required=True); p.add_argument('--input-csv',required=True); p.add_argument('--output-dir',required=True); p.add_argument('--run-id',default='lobot-e2-v2-r2-rescored-v1'); p.add_argument('--source-run-id',required=True); a=p.parse_args()
 doc,sha=protocol(a.protocol); cases={c['case_id']:c for c in doc['cases']}; src=Path(a.input_csv); rows=list(csv.DictReader(src.open(encoding='utf-8')))
 out=Path(a.output_dir); out.mkdir(parents=True,exist_ok=True); target=out/(a.run_id+'.csv')
 if target.exists(): raise SystemExit(f'REFUSING_TO_OVERWRITE:{target}')
 for row in rows:
  case=cases[row['case_id']]
  try:
   parsed=json.loads(row.get('raw_response') or '{}'); vr=deterministic_output_validation(parsed,case['model_input']); row.update(vr.to_dict()); row.update(reference_scoring(vr,parsed,case['evaluation_reference'])); row['validator_codes']=json.dumps(vr.validator_codes); row['constraint_results']=json.dumps(row['constraint_results'],sort_keys=True); row['source_run_id']=a.source_run_id; row['rescoring_git_commit']=subprocess.run(['git','rev-parse','HEAD'],capture_output=True,text=True).stdout.strip()
  except Exception as e: row['failure_reason']=type(e).__name__
 with target.open('w',newline='',encoding='utf-8') as h:
  fields=list(dict.fromkeys(RESULT_FIELDS + list(rows[0].keys()) + ['source_run_id','rescoring_git_commit'])); w=csv.DictWriter(h,fieldnames=fields); w.writeheader(); w.writerows(rows)
 summary=build_e2_summary(rows,{'model_name':rows[0].get('model_name'),'model_digest':rows[0].get('model_digest'),'generation_parameters':rows[0].get('generation_parameters')},'v2',sha,a.run_id,rows[0].get('variant','plain_llm')); summary.update(source_run_id=a.source_run_id,rescoring_git_commit=subprocess.run(['git','rev-parse','HEAD'],capture_output=True,text=True).stdout.strip(),validator_version='grounding_v2'); (out/(a.run_id+'_summary.json')).write_text(json.dumps(summary,indent=2),encoding='utf-8'); print(target)
if __name__=='__main__': main()






