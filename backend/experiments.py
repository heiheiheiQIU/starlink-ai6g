"""Paired synthetic rule validation on the preregistered matrix; no AI/optimizer claims."""
import argparse
import copy
import csv
import hashlib
import json
from pathlib import Path
import random
from uuid import uuid4

from backend.cli import RunConfig,_hash,_write_json
from backend.policies.runner import run_policy


def build_config(cell,seed):
    root=Path(__file__).resolve().parents[1]
    data=json.loads((root/'configs/scenarios/r3_normal.json').read_text(encoding='utf-8'))
    scene=data['scenario'];scene['scenario_id']=f"r5_{cell['cell_id']}_{seed}"
    initial={'low':.8,'medium':1.2,'ample':10.0}[cell['energy_margin']]
    count={'low':2,'near_capacity':6,'overload':10}[cell['load_level']]
    strong=cell['link_disturbance']=='strong'
    scene['initial_energy_Wh']=initial
    scene['channel']=dict(version='time-indexed-sha256-v1',seed=seed,step_s=.25,ack_loss_prob=.12 if strong else .02)
    health=scene['health_observations'][0]
    health.update(soc_est=initial/20,soc_lower=initial/20,energy_lower_Wh=initial,
                  model_version='synthetic-r5-accurate-health',uncertainty_method='synthetic_exact_counterexample')
    task_template=scene['tasks'][0];scene['tasks']=[]
    # A separate namespace: task generation never consumes the channel sequence.
    task_seed=int.from_bytes(hashlib.sha256(f'tasks-v1|{seed}'.encode()).digest()[:8],'big')
    rng=random.Random(task_seed)
    for index in range(count):
        task=copy.deepcopy(task_template);arrival=float(index*2)
        payload=1024*rng.choice((1,2))
        task.update(task_id=f'T{index:02d}',arrival_s=arrival,deadline_s=min(24.0,arrival+rng.choice((6.0,10.0))),
                    payload_bytes=payload,remaining_bytes=payload,priority_weight=float(1+index%3))
        scene['tasks'].append(task)
    for windows in ('true_windows','forecast_windows'):
        scene[windows][0]['end_s']=26.0
        scene[windows][0]['loss_profile'][0].update(robust_loss_prob=.2 if strong else .05,fast_loss_prob=.4 if strong else .12)
    data.update(kind='rule_validation',evaluation_end_s=24.0,actions=[])
    return RunConfig.model_validate(data).model_dump()


def run_matrix(matrix_path:Path,output:Path,*,limit=None):
    if output.exists() and any(output.iterdir()):raise ValueError('Output must be new or empty')
    planned=json.loads(matrix_path.read_text(encoding='utf-8'))
    trajectories=planned['trajectories'];cells={c['cell_id']:c for c in planned['cells']}
    if limit is not None:
        if isinstance(limit,bool) or not isinstance(limit,int) or limit<1:raise ValueError('Positive limit required')
        trajectories=trajectories[:limit]
    output.mkdir(parents=True,exist_ok=True);(output/'configs').mkdir()
    _write_json(output/'status.json',dict(status='running',completed_trajectories=0))
    rows=[];config_hashes={};source_hashes={};revision=None
    batch_id='r5_'+uuid4().hex
    fields=['trajectory_id','cell_id','seed','policy_id','run_id','input_hash','config_hash','weighted_on_time_rate',
            'success_payload_bytes','goodput_bps','joule_per_success_bit','energy_violation_count']
    try:
        with (output/'per_run.csv').open('w',encoding='utf-8',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');writer.writeheader()
            for trace in trajectories:
                identity=trace['trajectory_id'];seed=trace['environment_seed'];cell=cells[trace['cell_id']]
                config=build_config(cell,seed);config_hashes[identity]=_hash(config)
                _write_json(output/'configs'/(identity+'.json'),config)
                common_hash=None
                for policy in ('edf','value'):
                    folder=output/'runs'/identity/policy
                    result=run_policy(config,folder,policy_id=policy,run_id=batch_id+'_'+identity)
                    if common_hash is not None and common_hash!=result['input_hash']:raise ValueError('Unpaired inputs')
                    common_hash=result['input_hash'];revision=result['code_revision'];metrics=result['by_policy'][0]
                    row=dict(trajectory_id=identity,cell_id=cell['cell_id'],seed=seed,policy_id=policy,
                        run_id=result['run_id'],input_hash=result['input_hash'],config_hash=result['config_hash'])
                    row.update({name:metrics[name] for name in fields if name in metrics})
                    rows.append(row);writer.writerow(row);stream.flush()
                    manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
                    source_hashes.update(manifest['source_sha256'])
                _write_json(output/'status.json',dict(status='running',completed_trajectories=len(rows)//2))
        summary=dict(kind='synthetic_rule_validation_not_AI_benchmark',trajectory_count=len(trajectories),policy_run_count=len(rows),by_policy={})
        for policy in ('edf','value'):
            values=[r for r in rows if r['policy_id']==policy]
            rates=[r['weighted_on_time_rate'] for r in values if r['weighted_on_time_rate'] is not None]
            summary['by_policy'][policy]=dict(sample_count=len(values),mean_weighted_on_time_rate=sum(rates)/len(rates) if rates else None,
                successful_payload_bytes=sum(r['success_payload_bytes'] for r in values),
                energy_violation_segments=sum(r['energy_violation_count'] or 0 for r in values))
        _write_json(output/'summary.json',summary)
        root=Path(__file__).resolve().parents[1]
        source_hashes['backend/experiments.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        _write_json(output/'manifest.json',dict(kind=summary['kind'],batch_id=batch_id,code_revision=revision,source_sha256=source_hashes,
            matrix_sha256=hashlib.sha256(matrix_path.read_bytes()).hexdigest(),configs_sha256=config_hashes,
            artifacts_sha256={name:hashlib.sha256((output/name).read_bytes()).hexdigest() for name in ('per_run.csv','summary.json')},
            note='Synthetic assumptions; fixed rules only; not the accepted held-out AI comparison. Per-run manifests preserve all detailed artifacts.'))
        _write_json(output/'status.json',dict(status='completed',completed_trajectories=len(trajectories)))
        return summary
    except BaseException as error:
        _write_json(output/'status.json',dict(status='failed',completed_policy_runs=len(rows),error=type(error).__name__))
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--matrix',type=Path,default=Path('experiments/test_matrix.json'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--limit',type=int)
    args=parser.parse_args();print(json.dumps(run_matrix(args.matrix,args.output,limit=args.limit)))


if __name__=='__main__':main()
