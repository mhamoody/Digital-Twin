from statistics import mean,median
def summarize(runs):
 v=[float(x) for x in runs];return {'n':len(v),'mean':mean(v) if v else 0.,'median':median(v) if v else 0.,'min':min(v) if v else 0.,'max':max(v) if v else 0.}
