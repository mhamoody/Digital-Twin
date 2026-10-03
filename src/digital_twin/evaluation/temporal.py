def cutoff_violations(features,checkpoint_time_key='checkpoint_time'):
 out=[]
 for r in features:
  for f in r.get('features',[]):
   if f.get('source_time') is not None and f['source_time']>r[checkpoint_time_key]:out.append({'learner_id':r.get('learner_id'),'presentation_id':r.get('presentation_id'),'checkpoint':r.get('checkpoint'),'feature_source':f.get('source'),'source_time':f['source_time']})
 return out
