MODES=('drop_incomplete','zero_or_default_imputation','missing_aware_abstention')
def classify(value,observed=True,due=True):
 if not observed:return 'missing'
 if not due:return 'not_due'
 return 'observed_zero' if value==0 else 'observed'
def coverage_error(predictions):
 c=[x for x in predictions if not x.get('abstained')];e=[x for x in c if x.get('error')];return {'coverage':len(c)/len(predictions) if predictions else 0.,'error_rate_covered':len(e)/len(c) if c else 0.,'abstention_rate':1-len(c)/len(predictions) if predictions else 0.}
