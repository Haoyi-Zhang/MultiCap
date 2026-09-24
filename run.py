#!/usr/bin/env python3
"""Reproduce bounded deterministic evidence using only the Python standard library.

Invocation: python run.py reproduce --out /tmp/bag-evidence
            python run.py check
Each command uses one process and one worker. No network or shell subprocesses.
"""
from __future__ import annotations
import argparse
import csv
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time
from collections import Counter
from itertools import product

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
from bags import denote, frame_bound, cardinality_bounds, check_program
from replay import Replay
from cache_search import solve
from cache_check import check
from negative_controls import run as cache_negative_controls
from residual import synthesize
from residual_check import check_residual
from integer_rank import solve_rank, compile_fragments, bilinear
from integer_rank_check import check_rank
from positive_source import canonical_source, probe_extract, const, xvar, yvar, add, mul
from positive_source_check import quotient_extract
from capability_cases import run_separations


def dump(path:Path,value)->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n',encoding='utf-8')


def rows_csv(path:Path,rows:list[dict])->None:
    if not rows:raise ValueError('cannot write empty CSV')
    fields=[]
    for row in rows:
        for key in row:
            if key not in fields:fields.append(key)
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='raise');w.writeheader();w.writerows(rows)


def vector_probes(n:int)->list[list[int]]:
    values={(0,)*n,(1,)*n,(2,)*n,tuple(i%2 for i in range(n)),tuple((i+1)%2 for i in range(n))}
    for i in range(n):
        e=[0]*n;e[i]=1;values.add(tuple(e));e=[0]*n;e[i]=2;values.add(tuple(e))
    return [list(v) for v in sorted(values)]


def source_negative_controls()->list[dict]:
    cases=[
        ('pure-left',xvar(0),False),('pure-right',yvar(0),False),('constant',const(1),False),
        ('left-square',mul(mul(xvar(0),xvar(0)),yvar(0)),False),
        ('right-square',mul(xvar(0),mul(yvar(0),yvar(0))),False),
        ('mixed-linear-nonlinear',add(mul(xvar(0),yvar(0)),mul(mul(xvar(0),xvar(0)),yvar(0))),False),
        ('dead-nonlinear',mul(const(0),mul(mul(xvar(0),xvar(0)),yvar(0))),True),
    ]
    rows=[]
    for name,expr,should_accept in cases:
        source={'left_tags':1,'right_tags':1,'expression':expr}
        outcomes=[]
        for label,fn in [('numeric-probe',probe_extract),('monomial-quotient',quotient_extract)]:
            accepted=True
            try:fn(source)
            except ValueError:accepted=False
            if accepted!=should_accept:raise AssertionError((name,label,accepted,should_accept))
            outcomes.append({'checker':label,'accepted':accepted})
        rows.append({'name':name,'expected_accept':should_accept,'outcomes':outcomes})
    return rows


def reproduce(out:Path)->None:
    if out.exists() and any(out.iterdir()):raise ValueError('Output directory must be empty')
    out.mkdir(parents=True,exist_ok=True)
    start=time.process_time();wall=time.monotonic()

    # 1. Restartable source semantics.
    cases=json.loads((ROOT/'inputs/semantic_cases.json').read_text())
    semantic=[];max_ops=max_arity=0
    for case in cases:
        p,db=case['program'],case['database']
        expected=denote(p,db)
        replay=Replay(p,db,read_limit=1_000_000)
        actual=Counter(replay.rows())
        bounds=cardinality_bounds(p,db)
        assert actual==expected,case['id']
        assert replay.stats.active_frames==0,case['id']
        assert replay.stats.peak_frames<=frame_bound(p),case['id']
        assert sum(actual.values())<=bounds[p['root']],case['id']
        assert replay.stats.max_counter<=max(bounds),case['id']
        schemas=check_program(p)
        max_ops=max(max_ops,len(p['nodes']));max_arity=max(max_arity,max(map(len,schemas)))
        semantic.append({'id':case['id'],'family':case['family'],'input_occurrences':sum(map(len,db.values())),
            'output_occurrences':sum(actual.values()),'base_reads':replay.stats.base_reads,
            'peak_logical_frames':replay.stats.peak_frames,'frame_bound':frame_bound(p),
            'maximum_counter':replay.stats.max_counter,'maximum_cardinality_bound':max(bounds),'equivalent':True})
    rows_csv(out/'semantic.csv',semantic)

    # 2. Occurrence-record cache certificates.
    cache_certificates=[];cache=[];cache_negatives=[]
    for case in json.loads((ROOT/'inputs/cache_cases.json').read_text()):
        packet=solve(case['n'],case['m'],case['capacity'])
        checked=check(packet)
        if (case['n'],case['m'],case['capacity'])==(3,3,3):cache_negatives=cache_negative_controls(packet)
        dump(out/'certificates'/(case['id']+'.json'),packet)
        cache_certificates.append(packet)
        cache.append({'id':case['id'],'n':case['n'],'m':case['m'],'capacity':case['capacity'],
            'optimal_reads':packet['optimum'],'search_states':packet['search_states'],
            'search_transitions':packet['search_transitions'],'potential_entries':checked['potential_entries'],
            'checked_inequalities':checked['checked_inequalities']})
    rows_csv(out/'cache.csv',cache)

    # 3. Positive-source admission, exact integer rank, and extracted schedules.
    rank_rows=[];rank_checks=[];numeric_comparisons=0;source_probes=0
    for case in json.loads((ROOT/'inputs/rank_cases.json').read_text()):
        matrix=case['matrix'];source=canonical_source(matrix)
        probed=probe_extract(source,max_coefficient=8)
        quotient=quotient_extract(source,max_coefficient=8)
        assert probed['matrix']==quotient['matrix']==matrix
        source_probes+=probed['probes']
        packet=solve_rank(matrix);checked=check_rank(packet)
        packet.update({'id':case['id'],'family':case['family'],'source':source,
                       'source_probe':probed,'source_quotient':quotient})
        dump(out/'certificates'/(case['id']+'.json'),packet)
        rank_checks.append(checked)
        xs=vector_probes(len(matrix));ys=vector_probes(len(matrix[0]))
        levels=sorted({0,min(1,packet['rank']),packet['rank']})
        for x,y,fast in product(xs,ys,levels):
            got=compile_fragments(packet,x,y,fast)
            want=bilinear(matrix,x,y)
            assert got['value']==want
            assert got['temporary_word_transfers']==2*max(0,packet['rank']-fast)
            numeric_comparisons+=1
        rank_rows.append({'id':case['id'],'family':case['family'],'rows':len(matrix),'cols':len(matrix[0]),
            'rank':packet['rank'],'rank_one_atoms':packet['atom_count'],
            'potential_states':checked['potential_states'],'checked_inequalities':checked['checked_inequalities'],
            'source_nodes':probed['nodes'],'source_probes':probed['probes'],
            'numeric_schedule_comparisons':len(xs)*len(ys)*len(levels)})
    rows_csv(out/'integer_rank.csv',rank_rows)

    # 4. Finite residual-state compiler in every possible Boolean 2x2 function.
    residual_rows=[];residual_checks=[]
    for case in json.loads((ROOT/'inputs/residual_cases.json').read_text()):
        # Compute minimal width from the zero-fast-bit variant, then test all
        # meaningful fast capacities and one redundant capacity above the width.
        first=synthesize(case['table'],0);variants=[]
        for fast in range(first['code_bits']+2):
            packet=synthesize(case['table'],fast);checked=check_residual(packet)
            variants.append(packet);residual_checks.append(checked)
        cert={'id':case['id'],'table':case['table'],'variants':variants}
        dump(out/'certificates'/(case['id']+'.json'),cert)
        residual_rows.append({'id':case['id'],'residual_classes':first['residual_classes'],
            'minimal_code_bits':first['code_bits'],'zero_fast_bit_transfers':first['temporary_bit_transfers'],
            'fast_capacities_checked':len(variants),
            'compiled_executions_checked':sum(c['executions_checked'] for c in residual_checks[-len(variants):])})
    rows_csv(out/'residual.csv',residual_rows)

    # 5. Cross-model witnesses and controls.
    separations=run_separations();rows_csv(out/'capability_separations.csv',separations)
    positive_negatives=source_negative_controls()
    dump(out/'negative_controls.json',{'cache':cache_negatives,'positive_source':positive_negatives})
    assert cache_negatives and len(cache_negatives)==26
    coarse=max(6,3+(9-2+1)//2)
    assert coarse==7 and next(x['optimal_reads'] for x in cache if x['n']==x['m']==x['capacity']==3)==8

    declared_instances=len(cases)+len(cache)+len(rank_rows)+len(residual_rows)
    assert declared_instances==985 and declared_instances<=1000
    cache_obligations=sum(x['search_transitions']+x['checked_inequalities'] for x in cache)
    rank_inequalities=sum(x['checked_inequalities'] for x in rank_rows)
    residual_executions=sum(x['compiled_executions_checked'] for x in residual_rows)
    obligations=(len(cases)*5+cache_obligations+len(cache_negatives)+rank_inequalities+
                 numeric_comparisons+source_probes+residual_executions+2*len(positive_negatives))
    assert obligations<=100_000,obligations
    summary={'declared_program_or_certificate_instances':declared_instances,
        'semantic_cases':len(cases),'template_families':len({c['family'] for c in cases}),
        'exhaustive_core_templates':11,'exhaustive_core_input_pairs':81,'boundary_cases':5,
        'semantic_failures':0,'cache_instances':len(cache),'cache_negative_controls':len(cache_negatives),
        'integer_rank_instances':len(rank_rows),'residual_function_instances':len(residual_rows),
        'positive_source_negative_controls':len(positive_negatives),'negative_control_failures':0,
        'maximum_operators':max_ops,'maximum_tuple_arity':max_arity,
        'maximum_base_reads_per_semantic_case':max(r['base_reads'] for r in semantic),
        'total_modeled_base_reads':sum(r['base_reads'] for r in semantic),
        'maximum_logical_frames':max(r['peak_logical_frames'] for r in semantic),
        'cache_search_transitions':sum(r['search_transitions'] for r in cache),
        'cache_certificate_inequalities':sum(r['checked_inequalities'] for r in cache),
        'rank_certificate_inequalities':rank_inequalities,
        'factor_schedule_numeric_comparisons':numeric_comparisons,
        'positive_bilinearity_probes':source_probes,
        'residual_compiled_executions':residual_executions,
        'counted_validation_and_transition_obligations':obligations,
        'rank_distribution':{str(k):sum(1 for r in rank_rows if r['rank']==k) for k in sorted({r['rank'] for r in rank_rows})},
        'cpu_seconds':time.process_time()-start,'wall_seconds':time.monotonic()-wall,
        'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'workers':1,'child_processes':0,'random_seed':None,
        'rss_scope':'whole Python harness including input data, Counter oracle, exact dynamic programs, and checkers; Linux KiB',
        'logical_memory_scope':'model-level state only; not Python allocation or a physical performance claim',
        'claim_scope':'finite executable cross-checks and proof certificates accompanying separately stated general theorems'}
    dump(out/'summary.json',summary)
    print(json.dumps(summary,indent=2,sort_keys=True))


def check_retained()->None:
    cache_checked=[]
    for path in sorted((ROOT/'results/certificates').glob('cache-*.json')):
        cache_checked.append({'certificate':path.name,**check(json.loads(path.read_text()))})
    if len(cache_checked)!=9:raise ValueError('Expected nine retained cache certificates')
    rank_checked=[]
    for path in sorted((ROOT/'results/certificates').glob('rank-*.json')):
        packet=json.loads(path.read_text());rank_checked.append(check_rank(packet))
        if probe_extract(packet['source'])['matrix']!=packet['matrix']:raise ValueError('retained source probe mismatch')
        if quotient_extract(packet['source'])['matrix']!=packet['matrix']:raise ValueError('retained quotient mismatch')
    if len(rank_checked)!=64:raise ValueError('Expected 64 retained rank certificates')
    residual_checked=[]
    for path in sorted((ROOT/'results/certificates').glob('residual-*.json')):
        cert=json.loads(path.read_text())
        if cert['table']!=cert['variants'][0]['table']:raise ValueError('residual table mismatch')
        residual_checked.extend(check_residual(v) for v in cert['variants'])
    if len(list((ROOT/'results/certificates').glob('residual-*.json')))!=16:
        raise ValueError('Expected 16 retained residual certificates')
    summary=json.loads((ROOT/'results/summary.json').read_text())
    with (ROOT/'results/semantic.csv').open(newline='') as f:semantic=list(csv.DictReader(f))
    with (ROOT/'results/integer_rank.csv').open(newline='') as f:rank_rows=list(csv.DictReader(f))
    with (ROOT/'results/residual.csv').open(newline='') as f:residual_rows=list(csv.DictReader(f))
    assert len(semantic)==summary['semantic_cases']==896
    assert len(rank_rows)==summary['integer_rank_instances']==64
    assert len(residual_rows)==summary['residual_function_instances']==16
    assert all(r['equivalent']=='True' for r in semantic)
    assert sum(int(r['base_reads']) for r in semantic)==summary['total_modeled_base_reads']
    negatives=json.loads((ROOT/'results/negative_controls.json').read_text())
    fresh_cache=cache_negative_controls(json.loads((ROOT/'results/certificates/cache-07.json').read_text()))
    assert fresh_cache==negatives['cache'] and len(fresh_cache)==summary['cache_negative_controls']==26
    assert source_negative_controls()==negatives['positive_source']
    print(json.dumps({'cache_certificates_checked':len(cache_checked),
        'rank_certificates_checked':len(rank_checked),'residual_variants_checked':len(residual_checked),
        'negative_controls':len(fresh_cache)+len(negatives['positive_source']),
        'retained_semantic_rows_reconciled':len(semantic),
        'declared_instances_reconciled':len(semantic)+len(cache_checked)+len(rank_checked)+16},indent=2))


def main()->None:
    if not __debug__:raise RuntimeError('Run without -O: assertions are required validation')
    if hasattr(signal,'alarm'):signal.alarm(115)
    resource.setrlimit(resource.RLIMIT_AS,(1536*1024**2,1536*1024**2))
    resource.setrlimit(resource.RLIMIT_CPU,(100,110))
    if hasattr(os,'sched_getaffinity') and hasattr(os,'sched_setaffinity'):
        available=os.sched_getaffinity(0);os.sched_setaffinity(0,{min(available)})
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['reproduce','check']);parser.add_argument('--out',type=Path)
    args=parser.parse_args()
    if args.command=='reproduce':
        if args.out is None:parser.error('reproduce requires --out')
        reproduce(args.out.resolve())
    else:check_retained()

if __name__=='__main__':
    try:main()
    except (AssertionError,ValueError,KeyError,RuntimeError,RecursionError) as error:
        print(f'VALIDATION FAILED: {error}',file=sys.stderr);sys.exit(1)
