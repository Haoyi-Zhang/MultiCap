"""Exact nonnegative-integer factorization rank for bounded tiny matrices.

For a target A, every factor column/row contributes a nonzero integer rank-one
atom R <= A.  Dynamic programming over all elementwise residual matrices finds
the minimum number of atoms.  The emitted certificate contains both a witness
and a Bellman potential over every residual state; integer_rank_check.py checks
it using independently generated atoms and transitions.
"""
from __future__ import annotations
from functools import lru_cache
from itertools import product
from typing import Iterable

Matrix=tuple[tuple[int,...],...]


def as_matrix(value) -> Matrix:
    a=tuple(tuple(int(x) for x in row) for row in value)
    if not a or not a[0] or any(len(row)!=len(a[0]) for row in a):
        raise ValueError('nonempty rectangular matrix required')
    if any(x<0 for row in a for x in row):raise ValueError('natural entries required')
    return a


def zero_like(a: Matrix) -> Matrix:
    return tuple(tuple(0 for _ in row) for row in a)


def leq(a: Matrix,b: Matrix)->bool:
    return all(x<=y for ra,rb in zip(a,b) for x,y in zip(ra,rb))


def sub(a:Matrix,b:Matrix)->Matrix:
    if not leq(b,a):raise ValueError('negative residual')
    return tuple(tuple(x-y for x,y in zip(ra,rb)) for ra,rb in zip(a,b))


def add(a:Matrix,b:Matrix)->Matrix:
    return tuple(tuple(x+y for x,y in zip(ra,rb)) for ra,rb in zip(a,b))


def outer(u:tuple[int,...],v:tuple[int,...])->Matrix:
    return tuple(tuple(x*y for y in v) for x in u)


def atoms_for(target: Matrix) -> list[tuple[Matrix,tuple[int,...],tuple[int,...]]]:
    m,n=len(target),len(target[0]);mx=max(max(r) for r in target)
    if mx==0:return []
    seen={}
    for u in product(range(mx+1),repeat=m):
        if not any(u):continue
        for v in product(range(mx+1),repeat=n):
            if not any(v):continue
            r=outer(u,v)
            if any(any(row) for row in r) and leq(r,target) and r not in seen:
                seen[r]=(tuple(u),tuple(v))
    return [(r,*seen[r]) for r in sorted(seen)]


def all_residuals(target:Matrix):
    flat=[x for row in target for x in row]
    m,n=len(target),len(target[0])
    for values in product(*[range(x+1) for x in flat]):
        yield tuple(tuple(values[i*n+j] for j in range(n)) for i in range(m))


def solve_rank(value) -> dict:
    a=as_matrix(value);zero=zero_like(a);atoms=atoms_for(a)
    @lru_cache(maxsize=None)
    def opt(state:Matrix):
        if state==zero:return (0,())
        best=None
        # Deterministic atom order makes results stable.
        for idx,(r,_u,_v) in enumerate(atoms):
            if leq(r,state):
                d,path=opt(sub(state,r));candidate=(1+d,(idx,)+path)
                if best is None or candidate[0]<best[0] or (candidate[0]==best[0] and candidate[1]<best[1]):
                    best=candidate
        if best is None:raise RuntimeError('unit atoms should make nonzero state reachable')
        return best
    rank,path=opt(a)
    potential=[]
    for state in all_residuals(a):
        d,_=opt(state);potential.append({'state':[list(r) for r in state],'value':d})
    witness=[]
    state=a
    for idx in path:
        r,u,v=atoms[idx]
        witness.append({'u':list(u),'v':list(v),'atom':[list(row) for row in r]})
        state=sub(state,r)
    assert state==zero
    return {'matrix':[list(r) for r in a],'rows':len(a),'cols':len(a[0]),
            'rank':rank,'witness':witness,'potential':potential,
            'atom_count':len(atoms),'model':'nonnegative integer factorization rank'}


def compile_fragments(packet:dict,x:list[int],y:list[int],fast_words:int)->dict:
    if len(x)!=packet['rows'] or len(y)!=packet['cols']:raise ValueError('dimension mismatch')
    summaries=[];fragments=[]
    for factor in packet['witness']:
        s=sum(a*b for a,b in zip(factor['u'],x));summaries.append(s)
        fragments.append(s*sum(a*b for a,b in zip(factor['v'],y)))
    r=packet['rank'];slow=max(0,r-fast_words)
    return {'value':sum(fragments),'summaries':summaries,'fragments':fragments,
            'temporary_word_transfers':2*slow}


def bilinear(matrix:list[list[int]],x:list[int],y:list[int])->int:
    return sum(matrix[i][j]*x[i]*y[j] for i in range(len(x)) for j in range(len(y)))
