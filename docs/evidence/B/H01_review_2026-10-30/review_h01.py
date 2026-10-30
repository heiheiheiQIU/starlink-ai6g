import hashlib, json, subprocess, sys
from pathlib import Path
from backend.contracts import HealthEstimate
from backend.health.estimator import estimate_health
from backend.health.legacy_adapter import HealthInputError
root=Path(__file__).resolve().parent
out=root.parent
e=root/'docs/evidence/A/H01_2026-10-29'
m=json.loads((e/'manifest.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
checks={n:sha(e/n)==v for n,v in m['artifact_sha256'].items()}
checks['config']=sha(root/m['config_path'])==m['config_sha256']
canonical=lambda x:(json.dumps(x,ensure_ascii=False,allow_nan=False,sort_keys=True,indent=2)+'\n').encode()
h=json.loads((e/'inputs/health_history_success.json').read_text())
checks['history']=hashlib.sha256(canonical(h)).hexdigest()==m['history_input_sha256']
checks['call']=hashlib.sha256(canonical(dict(history=h,now_s=m['now_s']))).hexdigest()==m['call_input_sha256']
for name,code in [('success',0),('invalid',2)]:
    p=subprocess.run([sys.executable,'-m','backend.health.estimator','--history',str(e/f'inputs/health_history_{name}.json'),'--now-s','10'],cwd=root,capture_output=True)
    (out/f'{name}.stdout.json').write_bytes(p.stdout)
    (out/f'{name}.stderr.json').write_bytes(p.stderr)
    checks[f'{name}_exit']=p.returncode==code
    if name=='success':
        result=HealthEstimate.model_validate_json(p.stdout)
        checks['independent_units']=abs(result.energy_lower_Wh-6.05)<1e-12 and result.capacity_Wh_est==12 and result.soc_est==.6
        checks['missing_rul']=result.rul_est is None and result.rul_unit is None and 'RUL_UNAVAILABLE' in result.reason_codes
    else: checks['rejection']=json.loads(p.stderr)['error_code']=='OBSERVATION_INVALID'
future=dict(h[0],soc_observed=.1,observed_at_s=11,available_at_s=12)
checks['future_excluded']=estimate_health(h+[future],10)==estimate_health(h,10)
checks['stale_timestamp_preserved']=estimate_health(h,100).observed_at_s==8
try:estimate_health([dict(h[0],source='legacy',raw_fraction=.5)],10)
except HealthInputError as error: checks['legacy_rejected']=error.code=='OBSERVATION_INVALID'
else:checks['legacy_rejected']=False
checks['frozen_contract_bytes']=(root/'backend/contracts.py').read_bytes()==(root.parents[2]/'backend/contracts.py').read_bytes()
assert all(checks.values()),checks
(out/'verification.json').write_text(json.dumps(dict(checks=checks,all_passed=True,source_revision=m['source_revision'],synthetic_only=True),indent=2)+'\n')
print(json.dumps(checks))
