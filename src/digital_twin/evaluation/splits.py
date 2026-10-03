import random
def deterministic_split(ids,seed=42,fractions=(.7,.15,.15)):
 v=sorted(set(ids));random.Random(seed).shuffle(v);a=int(len(v)*fractions[0]);b=a+int(len(v)*fractions[1]);return {'train':v[:a],'validation':v[a:b],'test':v[b:]}
