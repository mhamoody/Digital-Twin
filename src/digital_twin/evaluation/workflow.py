STATES=('new_concern','reviewed','ongoing','resolved','dismissed')
def assert_separation(before,after):
 for k in ('prediction','evidence','support_case','support_action'):
  if before.get(k)!=after.get(k):raise AssertionError(f'workflow action mutated {k}')
