"""Bounded exact all-pairs cache oracle; initial unsymmetrized implementation, no external code."""
from collections import deque
import time,resource,json,signal,os
signal.alarm(115)
if hasattr(os,"sched_getaffinity"):
 os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
resource.setrlimit(resource.RLIMIT_AS,(1500*1024*1024,1500*1024*1024))
resource.setrlimit(resource.RLIMIT_CPU,(30,30))
n=m=3; capacity=3
N=n+m; target=(1<<(n*m))-1
edges={c:sum(1<<(i*m+j) for i in range(n) for j in range(m) if c>>i&1 and c>>(n+j)&1) for c in range(1<<N)}
start=(0,0); q=deque([start]); d={start:0}; parent={}; trials=0
t0=time.process_time()
while q:
 s=q.popleft(); cache,done=s
 if done==target: break
 for x in range(N):
  if cache>>x&1: continue
  evicts=[-1] if cache.bit_count()<capacity else [i for i in range(N) if cache>>i&1]
  for ev in evicts:
   trials+=1
   if trials>100000: raise RuntimeError('transition budget exceeded')
   c=(cache if ev<0 else cache&~(1<<ev))|(1<<x)
   t=(c,done|edges[c])
   if t not in d:
    d[t]=d[s]+1; parent[t]=(s,x,ev); q.append(t)
else: raise RuntimeError('infeasible')
steps=[]; goal=s
while s!=start:
 p,x,ev=parent[s]; steps.append({'load':x,'evict':None if ev<0 else ev});s=p
steps.reverse()
print(json.dumps({'n':n,'m':m,'M':capacity,'reads':d[goal],'states_discovered':len(d),'transitions_examined':trials,'cpu_seconds':time.process_time()-t0,'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'trace':steps},indent=2))
