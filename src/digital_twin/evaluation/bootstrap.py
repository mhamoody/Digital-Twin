from __future__ import annotations
import random

def bootstrap(values, statistic, seed=42, resamples=1000):
    values=list(values)
    if not values:return {"estimate":None,"lower_95_ci":None,"upper_95_ci":None,"resamples":0}
    estimate=statistic(values);rng=random.Random(seed);samples=[]
    for _ in range(resamples):
        sample=[values[rng.randrange(len(values))] for _ in values]
        try:
            value=statistic(sample)
            if value is not None and value==value:samples.append(value)
        except (ValueError,ZeroDivisionError):pass
    if not samples:return {"estimate":estimate,"lower_95_ci":None,"upper_95_ci":None,"resamples":0}
    samples.sort();return {"estimate":estimate,"lower_95_ci":samples[int(.025*len(samples))],"upper_95_ci":samples[max(0,int(.975*len(samples))-1)],"resamples":len(samples)}
