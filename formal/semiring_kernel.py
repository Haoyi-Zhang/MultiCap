"""Independent natural-semiring normalization for extracted factor schedules."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple,Union

@dataclass(frozen=True)
class Const: value:int
@dataclass(frozen=True)
class Var: name:str
@dataclass(frozen=True)
class Add: left:'Expr'; right:'Expr'
@dataclass(frozen=True)
class Mul: left:'Expr'; right:'Expr'
Expr=Union[Const,Var,Add,Mul]
Monomial=Tuple[str,...]
Polynomial=dict[Monomial,int]

def normalize(e:Expr)->Polynomial:
    if isinstance(e,Const):
        if e.value<0:raise ValueError('natural coefficients only')
        return {} if e.value==0 else {():e.value}
    if isinstance(e,Var):return {(e.name,):1}
    if isinstance(e,Add):
        out=normalize(e.left)
        for m,c in normalize(e.right).items():out[m]=out.get(m,0)+c
        return {m:c for m,c in out.items() if c}
    a=normalize(e.left);b=normalize(e.right);out={}
    for ma,ca in a.items():
        for mb,cb in b.items():
            m=tuple(sorted(ma+mb));out[m]=out.get(m,0)+ca*cb
    return {m:c for m,c in out.items() if c}

def add_many(xs):
    out=Const(0)
    for x in xs:out=Add(out,x)
    return out

def mul_const(c,e):return Mul(Const(c),e)

def target_expression(matrix):
    return add_many(mul_const(matrix[i][j],Mul(Var(f'x{i}'),Var(f'y{j}')))
        for i in range(len(matrix)) for j in range(len(matrix[0])))

def compiled_expression(witness):
    terms=[]
    for f in witness:
        left=add_many(mul_const(c,Var(f'x{i}')) for i,c in enumerate(f['u']))
        right=add_many(mul_const(c,Var(f'y{j}')) for j,c in enumerate(f['v']))
        terms.append(Mul(left,right))
    return add_many(terms)

def verify_factor_packet(packet)->dict:
    target=normalize(target_expression(packet['matrix']))
    compiled=normalize(compiled_expression(packet['witness']))
    if target!=compiled:raise ValueError('factor schedule polynomial mismatch')
    return {'variables':len(packet['matrix'])+len(packet['matrix'][0]),
            'target_monomials':len(target),'compiled_monomials':len(compiled),'checked':True}
