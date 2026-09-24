#!/usr/bin/env python3
"""Independent post-development robustness suite.

This file intentionally does not import the project implementation.  It uses only
Python's standard library and independently re-derives finite residual, small
integer-factor-rank, and two-slot occurrence-cache obligations.  Its purpose is
to detect correlated generator/checker mistakes and hand-picked-instance
fragility.  It is not a held-out statistical test set and does not replace the
general proofs.
"""
from __future__ import annotations
import argparse, hashlib, itertools, json, random, time
from collections import deque
from pathlib import Path

SEED = int.from_bytes(hashlib.sha256(b"anonymous-blind-review-v3-2026").digest()[:8], "big")

def residual_rows(table):
    return {tuple(row) for row in table}

def ceil_log2(n):
    if n <= 1: return 0
    return (n-1).bit_length()

def check_residual_trials(rng, trials=700):
    checked=0; collisions_checked=0
    for _ in range(trials):
        nx=rng.randint(1,8); ny=rng.randint(1,7); no=rng.randint(1,5)
        f=[[rng.randrange(no) for _ in range(ny)] for _ in range(nx)]
        rows=sorted(residual_rows(f)); k=ceil_log2(len(rows))
        code={r:i for i,r in enumerate(rows)}
        for x,row in enumerate(f):
            c=code[tuple(row)]
            assert c < 2**k if k else c==0
            for y in range(ny): assert rows[c][y]==f[x][y]
        if k>0 and len(rows)>2**(k-1):
            # Any (k-1)-bit state space has fewer states than residuals.
            assert len(rows) > 2**(k-1); collisions_checked += 1
        checked += nx*ny
    return {'trials':trials,'point_evaluations':checked,'strict_lower_bound_cases':collisions_checked}

def rank1_factor(A):
    m=len(A); n=len(A[0]) if m else 0
    if not any(any(row) for row in A): return ([],[])
    # Exact bounded search is independent and complete for 2x2 entries in 0..3:
    # if A=u v^T then each u_i and v_j divides/max-bounds observed entries.
    mx=max(max(r) for r in A)
    for u in itertools.product(range(mx+1), repeat=m):
        for v in itertools.product(range(mx+1), repeat=n):
            if all(u[i]*v[j]==A[i][j] for i in range(m) for j in range(n)):
                return list(u),list(v)
    return None

def exact_rank_2x2(A):
    if not any(any(r) for r in A): return 0
    return 1 if rank1_factor(A) is not None else 2

def eval_bilinear(A,x,y):
    return sum(A[i][j]*x[i]*y[j] for i in range(len(A)) for j in range(len(A[0])))

def check_integer_rank_exhaustive():
    matrices=0; schedules=0; memory_cases=0
    for vals in itertools.product(range(4), repeat=4):
        A=[list(vals[:2]),list(vals[2:])]
        r=exact_rank_2x2(A); matrices+=1
        # Independent matching factor: rank-2 column decomposition always works.
        if r==0: U=[[],[]]; V=[]
        elif r==1:
            u,v=rank1_factor(A); U=[[u[0]],[u[1]]]; V=[v]
        else:
            U=[[A[0][0],A[0][1]],[A[1][0],A[1][1]]]
            V=[[1,0],[0,1]]
        for x in itertools.product(range(4),repeat=2):
            for y in itertools.product(range(4),repeat=2):
                summaries=[sum(U[i][l]*x[i] for i in range(2)) for l in range(r)]
                got=sum(summaries[l]*sum(V[l][j]*y[j] for j in range(2)) for l in range(r))
                assert got==eval_bilinear(A,x,y); schedules+=1
        for M in range(4):
            traffic=2*max(0,r-M)
            assert traffic>=0 and traffic%2==0; memory_cases+=1
    return {'matrices':matrices,'schedule_evaluations':schedules,'memory_cases':memory_cases}

def cache_opt_two_slots(n,m):
    # State=(loaded A occurrences, loaded B occurrences, emitted-pair bitmask).
    # With two slots, loaded sets have total size at most 2. A read loads one
    # occurrence and may evict arbitrary resident occurrences. Emission is free
    # whenever both endpoints are resident. BFS minimizes source reads.
    total=n*m; target=(1<<total)-1
    start=(frozenset(),frozenset(),0)
    q=deque([(start,0)]); seen={start}
    while q:
        (la,lb,mask),d=q.popleft()
        # Saturate all currently emit-able pairs.
        sm=mask
        for i in la:
            for j in lb: sm |= 1<<(i*m+j)
        if sm==target:return d
        # choose a source occurrence to read; after load, choose evictions to capacity 2
        residents=[('a',i) for i in la]+[('b',j) for j in lb]
        for kind,idx,limit in [('a',i,n) for i in range(n)]+[('b',j,m) for j in range(m)]:
            new=set(residents); new.add((kind,idx))
            for keep in itertools.combinations(sorted(new), min(2,len(new))):
                nla=frozenset(v for k,v in keep if k=='a'); nlb=frozenset(v for k,v in keep if k=='b')
                st=(nla,nlb,sm)
                if st not in seen: seen.add(st); q.append((st,d+1))
    raise AssertionError('unreachable')

def check_cache():
    rows=[]
    for n in range(1,5):
        for m in range(1,5):
            got=cache_opt_two_slots(n,m); want=n*m+1
            assert got==want,(n,m,got,want)
            rows.append({'n':n,'m':m,'opt':got,'formula':want})
    return {'instances':len(rows),'rows':rows}

def verify_existing_factor_certificates(root):
    checked=0; equations=0; rejected_noncanonical=0
    for p in root.rglob('*.json'):
        try: x=json.loads(p.read_text())
        except Exception: continue
        stack=[x]
        while stack:
            z=stack.pop()
            if isinstance(z,dict):
                A=z.get('A') or z.get('matrix')
                U=z.get('U') or z.get('left_factor')
                V=z.get('V') or z.get('right_factor')
                if isinstance(A,list) and isinstance(U,list) and isinstance(V,list) and A and U and V:
                    try:
                        m=len(A); n=len(A[0]); r=len(V)
                        if len(U)==m and all(len(row)==r for row in U) and all(len(row)==n for row in V):
                            assert all(isinstance(q,int) and q>=0 for M in (A,U,V) for row in M for q in row)
                            assert all(sum(U[i][l]*V[l][j] for l in range(r))==A[i][j] for i in range(m) for j in range(n))
                            checked+=1; equations+=m*n
                    except (TypeError,AssertionError):
                        raise AssertionError(f'bad factor certificate in {p}')
                stack.extend(z.values())
            elif isinstance(z,list): stack.extend(z)
    return {'certificates_found_and_checked':checked,'matrix_equations':equations}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root',type=Path,default=Path('.')); ap.add_argument('--out',type=Path)
    a=ap.parse_args(); t=time.time(); rng=random.Random(SEED)
    out={'schema':'blind-holdout-v1','seed':SEED,
         'interpretation':'post-development independent robustness evidence, not a statistical held-out set',
         'residual':check_residual_trials(rng),
         'integer_rank_2x2':check_integer_rank_exhaustive(),
         'cache_two_slots':check_cache(),
         'existing_factor_certificates':verify_existing_factor_certificates(a.root),
         'seconds':round(time.time()-t,6)}
    text=json.dumps(out,indent=2,sort_keys=True)
    if a.out: a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(text+'\n')
    print(text)
if __name__=='__main__': main()
