"""Independent checker for tiny integer-rank certificates."""
from __future__ import annotations
from itertools import product


def mat(value):
    a=tuple(tuple(int(x) for x in row) for row in value)
    if not a or not a[0] or any(len(r)!=len(a[0]) for r in a):raise ValueError('bad matrix')
    if any(x<0 for r in a for x in r):raise ValueError('negative')
    return a

def outer(u,v):return tuple(tuple(x*y for y in v) for x in u)
def leq(a,b):return all(x<=y for ra,rb in zip(a,b) for x,y in zip(ra,rb))
def subtract(a,b):return tuple(tuple(x-y for x,y in zip(ra,rb)) for ra,rb in zip(a,b))
def plus(a,b):return tuple(tuple(x+y for x,y in zip(ra,rb)) for ra,rb in zip(a,b))

def independent_atoms(target):
    m,n=len(target),len(target[0]);mx=max(max(r) for r in target);found={}
    # Different loop nesting and canonicalization from the solver.
    for v in product(range(mx+1),repeat=n):
        for u in product(range(mx+1),repeat=m):
            if not any(u) or not any(v):continue
            r=outer(u,v)
            if any(z for row in r for z in row) and leq(r,target):
                old=found.get(r)
                pair=(u,v)
                if old is None or pair<old:found[r]=pair
    return found

def check_rank(packet):
    a=mat(packet['matrix']);m,n=len(a),len(a[0]);zero=tuple(tuple(0 for _ in range(n)) for _ in range(m))
    if packet['rows']!=m or packet['cols']!=n:raise ValueError('dimensions')
    atoms=independent_atoms(a)
    total=zero
    for f in packet['witness']:
        u=tuple(f['u']);v=tuple(f['v']);r=mat(f['atom'])
        if len(u)!=m or len(v)!=n or r!=outer(u,v) or r not in atoms:raise ValueError('bad factor')
        total=plus(total,r)
    if total!=a or len(packet['witness'])!=packet['rank']:raise ValueError('bad upper witness')
    potentials={mat(item['state']):item['value'] for item in packet['potential']}
    expected=1
    for row in a:
        for x in row:expected*=x+1
    if len(potentials)!=expected or potentials.get(zero)!=0 or potentials.get(a)!=packet['rank']:
        raise ValueError('incomplete potential')
    inequalities=0
    for s,h in potentials.items():
        if h<0:raise ValueError('negative potential')
        if s!=zero and h<1:raise ValueError('nonzero state has zero potential')
        for r in atoms:
            if leq(r,s):
                nxt=subtract(s,r)
                if nxt not in potentials:raise ValueError('successor omitted')
                if h>1+potentials[nxt]:raise ValueError('potential can drop by more than one')
                inequalities+=1
    return {'rank':packet['rank'],'witness_factors':len(packet['witness']),
            'potential_states':len(potentials),'checked_inequalities':inequalities,
            'independent_atoms':len(atoms)}
