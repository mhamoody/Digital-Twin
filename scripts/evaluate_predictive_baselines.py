from __future__ import annotations
import argparse, csv, json
from pathlib import Path
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

def rows(path):
    with Path(path).open(encoding='utf-8', newline='') as h: return list(csv.DictReader(h))
def num(v):
    try: return float(v)
    except (TypeError, ValueError): return 0.0
def bootstrap(y, s, t, metric, seed=42, n=1000):
    rng=np.random.default_rng(seed); vals=[]; y=np.asarray(y); s=np.asarray(s)
    for _ in range(n):
        idx=rng.integers(0,len(y),len(y)); yy,ss=y[idx],s[idx]
        if metric in ('auroc','ap') and len(np.unique(yy))<2: continue
        vals.append(roc_auc_score(yy,ss) if metric=='auroc' else average_precision_score(yy,ss) if metric=='ap' else f1_score(yy,ss>=t,zero_division=0))
    return (None,None) if not vals else (float(np.quantile(vals,.025)),float(np.quantile(vals,.975)))
def main():
    p=argparse.ArgumentParser(); p.add_argument('--states',required=True); p.add_argument('--labels',required=True); p.add_argument('--features',required=True); p.add_argument('--splits',required=True); p.add_argument('--output',default='evaluation/results/e1_predictive.csv'); a=p.parse_args()
    states=rows(a.states); label_rows=rows(a.labels); label_by_learner={r['learner_id']:int(r.get('non_success', r.get('at_risk', 0))) for r in label_rows}; labels={r['state_id']:label_by_learner[r['learner_id']] for r in states}; fs=rows(a.features); names=sorted({r['feature_name'] for r in fs}); X={r['state_id']:{n:0.0 for n in names} for r in states}
    for r in fs:
        if r['state_id'] in X: X[r['state_id']][r['feature_name']]=num(r['value'])
    parts={r['learner_id']:r['partition'] for r in rows(a.splits)}; rec=[r for r in states if r['learner_id'] in parts]; out=[]
    for cp in sorted({int(r['checkpoint']) for r in rec}):
        tr=[r for r in rec if int(r['checkpoint'])==cp and parts[r['learner_id']]=='train']; va=[r for r in rec if int(r['checkpoint'])==cp and parts[r['learner_id']]=='validation']; te=[r for r in rec if int(r['checkpoint'])==cp and parts[r['learner_id']]=='test']
        model=make_pipeline(StandardScaler(),LogisticRegression(max_iter=1000,class_weight='balanced',random_state=42)); model.fit(np.array([[X[r['state_id']][n] for n in names] for r in tr]),[labels[r['state_id']] for r in tr])
        yv=np.array([labels[r['state_id']] for r in va]); sv=model.predict_proba(np.array([[X[r['state_id']][n] for n in names] for r in va]))[:,1]; ts=np.linspace(.1,.9,81); threshold=max(ts,key=lambda t:f1_score(yv,sv>=t,zero_division=0))
        yt=np.array([labels[r['state_id']] for r in te]); st=model.predict_proba(np.array([[X[r['state_id']][n] for n in names] for r in te]))[:,1]; pred=st>=threshold; tn,fp,fn,tp=confusion_matrix(yt,pred,labels=[0,1]).ravel(); row={'checkpoint':cp,'train_n':len(tr),'validation_n':len(va),'test_n':len(te),'test_positive':int(yt.sum()),'threshold':float(threshold),'auroc':float(roc_auc_score(yt,st)),'average_precision':float(average_precision_score(yt,st)),'precision':float(precision_score(yt,pred,zero_division=0)),'recall':float(recall_score(yt,pred,zero_division=0)),'f1':float(f1_score(yt,pred,zero_division=0)),'tn':int(tn),'fp':int(fp),'fn':int(fn),'tp':int(tp)}
        for m in ('auroc','ap','f1'):
            lo,hi=bootstrap(yt,st,threshold,m); row[m+'_ci_low']=lo; row[m+'_ci_high']=hi
        out.append(row)
    Path(a.output).parent.mkdir(parents=True,exist_ok=True)
    with Path(a.output).open('w',newline='',encoding='utf-8') as h: w=csv.DictWriter(h,fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
    Path(a.output).with_name('e1_feature_manifest.json').write_text(json.dumps({'feature_names':names,'label_source':str(Path(a.labels)),'train_only_fit':True,'threshold_selection':'validation_f1','seed':42},indent=2),encoding='utf-8')
    print(json.dumps({'status':'E1 LOGISTIC BASELINE = COMPLETED','checkpoints':out},indent=2))
if __name__=='__main__': main()


