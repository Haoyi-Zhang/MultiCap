#!/usr/bin/env python3
"""Fail-closed final internal gate for the released artifact."""
from __future__ import annotations
import argparse,hashlib,json,os,shutil,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def run(name,cmd,cwd=ROOT,timeout=7200):
 t=time.time();p=subprocess.run(cmd,cwd=cwd,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','LC_ALL':'C.UTF-8'},stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=timeout)
 return {'name':name,'command':cmd,'returncode':p.returncode,'seconds':round(time.time()-t,3),'output_tail':(p.stdout or '')[-4000:]}

def normalized_json(path):
 x=json.loads(path.read_text());
 for k in ('seconds','cpu_seconds','wall_seconds','elapsed_seconds','peak_rss_kb','generated_at','timestamp'):x.pop(k,None)
 return x

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--quick',action='store_true');ap.add_argument('--out',type=Path);a=ap.parse_args()
 checks=[]
 optional=[('reviewer_static',[sys.executable,'reviewer/static_release_audit.py']),('reviewer_claims',[sys.executable,'reviewer/audit_claims.py']),('reviewer_code_quality',[sys.executable,'reviewer/code-quality-audit.py']),('reviewer_contract',[sys.executable,'reviewer/manuscript_contract_audit.py']),('crosscheck_export',[sys.executable,'crosscheck/check_export.py']),('crosscheck_js',['node','crosscheck/check_rank_factorizations.mjs']),('crosscheck_mutation',[sys.executable,'crosscheck/mutation_test.py'])]
 for name,cmd in optional:
  if (ROOT/cmd[-1]).exists() if len(cmd)>1 and isinstance(cmd[-1],str) else True:
   try:checks.append(run(name,cmd))
   except FileNotFoundError:checks.append({'name':name,'returncode':127,'output_tail':'required executable missing'})
 checks.append(run('run_check',[sys.executable,'run.py','check']))
 checks.append(run('unittest',[sys.executable,'-m','unittest','discover','-s','tests','-v']))
 if (ROOT/'formal/check.py').exists():checks.append(run('formal',[sys.executable,'formal/check.py']))
 if (ROOT/'formal/lean/check.sh').exists():checks.append(run('lean',['sh','formal/lean/check.sh']))
 with tempfile.TemporaryDirectory(prefix='rs-final-gate-') as td:
  td=Path(td)
  checks.append(run('blind_holdout',[sys.executable,'reviewer/blind_holdout.py','--root','.', '--out',str(td/'blind.json')]))
  checks.append(run('fresh_campaign',[sys.executable,'reviewer/fresh_campaign.py','--out-dir',str(td/'fresh')]))
  retained=ROOT/'results/reviewer/fresh-campaign/summary.json'
  same=retained.exists() and normalized_json(retained)==normalized_json(td/'fresh/summary.json')
  checks.append({'name':'fresh_campaign_retained_comparison','returncode':0 if same else 1,'seconds':0,'output_tail':f'equal={same}'})
  if not a.quick:
   checks.append(run('reproduce',[sys.executable,'run.py','reproduce','--out',str(td/'reproduce')]))
 # Remove transient bytecode before hygiene check.
 for p in ROOT.rglob('__pycache__'):shutil.rmtree(p,ignore_errors=True)
 for p in ROOT.rglob('*.pyc'):
  try:p.unlink()
  except OSError:pass
 if (ROOT/'audit.py').exists():checks.append(run('package_clean',[sys.executable,'audit.py','--package-clean']))
 failed=[x['name'] for x in checks if x.get('returncode')!=0]
 out={'schema':'final-internal-gate-v1','status':'PASS' if not failed else 'FAIL','failed':failed,'checks':checks,
      'boundary':'Internal consistency and reproducibility gate; not external peer review, novelty proof, or acceptance guarantee.'}
 text=json.dumps(out,indent=2,ensure_ascii=False)
 if a.out:a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(text+'\n')
 print(text)
 raise SystemExit(0 if not failed else 1)
if __name__=='__main__':main()
