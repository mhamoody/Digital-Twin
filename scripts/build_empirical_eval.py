from __future__ import annotations
import argparse,csv,hashlib,json,random,subprocess
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
from digital_twin.schemas import DataOrigin
from digital_twin.state.builder import build_weekly_states

def read(path):
 with open(path,encoding='utf-8-sig',newline='') as h:return list(csv.DictReader(h))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--prepared',required=True);p.add_argument('--out',required=True);p.add_argument('--seed',type=int,default=42);a=p.parse_args();src=Path(a.prepared);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 enrol=read(src/'enrolments.csv'); acts=read(src/'activity_observations.csv'); ass=read(src/'assessments.csv'); obs=read(src/'assessment_observations.csv'); outcomes=read(src/'outcomes_restricted.csv')
 states=build_weekly_states(enrolments=enrol,activities=acts,assessments=ass,assessment_observations=obs,checkpoints=(3,5,8,10),built_at=datetime.now(timezone.utc),data_origin=DataOrigin.EMPIRICAL)
 labels={r['learner_id']:{'final_result':r['final_result'],'at_risk':int(r['non_success'])} for r in outcomes}; state_rows=[];feature_rows=[]
 for s in states:
  d=s.model_dump(mode='json'); label=labels.get(s.learner_id); state_rows.append({'state_id':s.state_id,'learner_id':s.learner_id,'presentation_id':s.presentation_id,'checkpoint':s.checkpoint_week,'checkpoint_time':s.cutoff_course_day,'eligible_at_checkpoint':True,'final_result':label['final_result'] if label else None,'at_risk':label['at_risk'] if label else None})
  for f in s.features: feature_rows.append({'state_id':s.state_id,'learner_id':s.learner_id,'presentation_id':s.presentation_id,'checkpoint':s.checkpoint_week,'checkpoint_time':s.cutoff_course_day,'feature_name':f.name,'value':f.value,'missing_reason':f.missing_reason.value if hasattr(f.missing_reason,'value') else str(f.missing_reason),'source_observation_count':f.source_observation_count,'provenance_reference':f.provenance_reference})
 with open(out/'states.csv','w',newline='',encoding='utf-8') as h:
  w=csv.DictWriter(h,fieldnames=list(state_rows[0]));w.writeheader();w.writerows(state_rows)
 with open(out/'features.csv','w',newline='',encoding='utf-8') as h:
  w=csv.DictWriter(h,fieldnames=list(feature_rows[0]));w.writeheader();w.writerows(feature_rows)
 # source-time audit uses the same cutoff and observation semantics as the canonical builder.
 act_by=defaultdict(list); obs_by=defaultdict(list)
 for r in acts:act_by[r['learner_id']].append(r)
 for r in obs:
  if r['is_banked']!='1':obs_by[r['learner_id']].append(r)
 temporal=[]
 for row in state_rows:
  cutoff=int(row['checkpoint_time']);lid=row['learner_id']
  for r in act_by[lid]:
   if int(r['course_day'])<=cutoff: temporal.append({'learner_id':lid,'presentation_id':row['presentation_id'],'checkpoint':row['checkpoint'],'source_type':'activity','source_id':r['source_record_id'],'source_time':int(r['course_day']),'checkpoint_time':cutoff})
  for r in obs_by[lid]:
   if int(r['submitted_course_day'])<=cutoff: temporal.append({'learner_id':lid,'presentation_id':row['presentation_id'],'checkpoint':row['checkpoint'],'source_type':'assessment_submission','source_id':r['source_record_id'],'source_time':int(r['submitted_course_day']),'checkpoint_time':cutoff})
 with open(out/'temporal_provenance.csv','w',newline='',encoding='utf-8') as h:
  w=csv.DictWriter(h,fieldnames=list(temporal[0]));w.writeheader();w.writerows(temporal)
 learners=sorted({r['learner_id'] for r in state_rows});rng=random.Random(a.seed);rng.shuffle(learners);n=len(learners);cuts=(int(n*.7),int(n*.85));parts={x:('train' if i<cuts[0] else 'validation' if i<cuts[1] else 'test') for i,x in enumerate(learners)}
 split=[{'learner_id':x,'partition':parts[x],'label':labels[x]['at_risk'],'seed':a.seed,'dataset_version':'oulad_AAA_2013J_v1'} for x in learners]
 with open(out/'split_manifest.csv','w',newline='',encoding='utf-8') as h:
  w=csv.DictWriter(h,fieldnames=list(split[0]));w.writeheader();w.writerows(split)
 commit=subprocess.run(['git','rev-parse','HEAD'],capture_output=True,text=True,check=False).stdout.strip() or 'unknown'; metadata={'dataset_version':'oulad_AAA_2013J_v1','presentation_id':'oulad:AAA:2013J','git_commit':commit,'source_prepared':str(src),'source_manifest_sha256':sha(src/'manifest.json'),'learners':len(learners),'states':len(state_rows),'checkpoint_counts':dict(Counter(r['checkpoint'] for r in state_rows)),'label_counts':dict(Counter(r['at_risk'] for r in state_rows)),'split_sizes':dict(Counter(x['partition'] for x in split)),'created_at':datetime.now(timezone.utc).isoformat()}
 for f in ('states.csv','features.csv','temporal_provenance.csv','split_manifest.csv'):metadata[f+'_sha256']=sha(out/f)
 (out/'metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8');print(json.dumps(metadata,indent=2))
if __name__=='__main__':main()

