"""Materialize and verify versioned, model-independent synthetic input candidates."""
import argparse
import copy
import hashlib
import itertools
import json
from pathlib import Path
import random
import shutil
import sys
import tempfile
import types

from backend.cli import RunConfig, _hash, _json_bytes


ROOT = Path(__file__).resolve().parents[1]
LOADS = ('low', 'near_capacity', 'overload')
ENERGIES = ('low', 'medium', 'ample')
LINKS = ('mild', 'strong')
DESCRIPTIONS = dict(
    load_definition='All tasks arrive at 0. Offered 4/12/20 payload blocks versus optimistic 12 blocks in 24s at 2s decision spacing. Deadline/ACK/loss constraints can reduce usable capacity.',
    health_assumption='Initial exact synthetic health; conservative energy propagation thereafter; RUL unavailable.',
    training_domain='All cells have nonzero forecast data loss, outside current deterministic teacher labeling domain.',
    leakage_review='Old development seeds excluded; A-N4b provenance and content audit pending delivery.')
RULES = dict(task_rng='random.Random(int.from_bytes(sha256(UTF8(formal-tasks-v1|seed))[:8],big))',
             deadline='Independent uniform choice from deadline_grid_s, then uniform(*priority_weight_range), task index order',
             energy='Initial exact health and energy from initial_energy_Wh[energy_margin], capacity20Wh; no solar or compute power',
             channel='time-indexed-sha256-v1; index=floor(Fraction(str(time_s))/Fraction(str(step_s))); key=version|seed|stream|index; streams=data,ack; SHA256 first8 bytes big endian shifted right11 divided by2**53')


def _read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def _validate_protocol(protocol):
    expected_cells = [dict(cell_id=f'cell_{i:02d}', load_level=load,
                           energy_margin=energy, link_disturbance=link)
                      for i, (load, energy, link) in enumerate(itertools.product(LOADS, ENERGIES, LINKS))]
    expected_traces = [dict(trajectory_id=f'formal_v1_{cell["cell_id"]}_trace_{j:02d}',
                            cell_id=cell['cell_id'], seed=200000+i*10+j)
                       for i, cell in enumerate(expected_cells) for j in range(10)]
    fixed = dict(schema_version='formal-input-protocol-v1', generator_version='formal-inputs-v1',
                 status='candidate_pending_review', evaluation_end_s=24.0, decision_dt_s=2.0,
                 task_counts=dict(low=2, near_capacity=6, overload=10), payload_bytes=2048,
                 deadline_grid_s=[8.0, 12.0, 18.0, 24.0], priority_weight_range=[1.0, 3.0],
                 initial_energy_Wh=dict(low=.8, medium=1.2, ample=10.0),
                 links=dict(mild=dict(data_robust=.05, data_fast=.12, ack=.02),
                            strong=dict(data_robust=.2, data_fast=.4, ack=.12)),
                 channel_step_s=.25, seed_start=200000, trajectories_per_cell=10,
                 model=None, cells=expected_cells, trajectories=expected_traces)
    fixed.update(DESCRIPTIONS, generation_rules=RULES)
    if set(protocol) != set(fixed):
        raise ValueError('Protocol fields differ from supported version')
    if any(protocol[key] != value for key, value in fixed.items()):
        raise ValueError('Protocol values differ from supported version')


def _assert_loaded_code():
    """Reject edits on disk after importing any of the generator's source modules."""
    if _source_hashes() != _IMPORT_HASHES:
        raise ValueError('Loaded code source snapshot changed after import')
    for name in _source_hashes():
        if not name.endswith('.py'):
            continue
        module = sys.modules[__name__] if name == 'backend/formal_inputs.py' else sys.modules.get(name[:-3].replace('/', '.'))
        if module is None:
            continue
        functions = []
        for value in vars(module).values():
            if isinstance(value, types.FunctionType) and value.__module__ == module.__name__:
                functions.append(value)
            elif isinstance(value, type) and value.__module__ == module.__name__:
                for member in vars(value).values():
                    member = member.__func__ if isinstance(member, (classmethod, staticmethod)) else member
                    if isinstance(member, types.FunctionType) and member.__module__ == module.__name__:
                        functions.append(member)
        functions = [function for function in functions
                     if Path(function.__code__.co_filename).as_posix().endswith(name)]
        if not functions:
            continue
        compiled = compile((ROOT/name).read_text(encoding='utf-8-sig'), functions[0].__code__.co_filename, 'exec', dont_inherit=True)
        expected = {}
        def collect(code):
            expected[code.co_qualname] = code
            for child in code.co_consts:
                if isinstance(child, types.CodeType):
                    collect(child)
        collect(compiled)
        for function in functions:
            if expected.get(function.__code__.co_qualname) != function.__code__:
                raise ValueError(f'Loaded code differs from source: {name}:{function.__qualname__}')


def _source_hashes():
    paths = ['backend/formal_inputs.py', 'backend/cli.py', 'backend/contracts.py',
             'configs/scenarios/r3_normal.json']
    paths.extend(p.relative_to(ROOT).as_posix() for p in sorted((ROOT/'backend/simulator').glob('*.py')))
    # Text-normalized identities are stable across Windows/Linux checkouts.
    return {name: hashlib.sha256((ROOT/name).read_text(encoding='utf-8-sig').encode()).hexdigest()
            for name in paths}


def _config(protocol, cell, trace, template):
    config = copy.deepcopy(template)
    scene = config['scenario']
    seed = trace['seed']
    scene['scenario_id'] = trace['trajectory_id']
    scene['initial_energy_Wh'] = protocol['initial_energy_Wh'][cell['energy_margin']]
    link = protocol['links'][cell['link_disturbance']]
    scene['channel'] = dict(version='time-indexed-sha256-v1', seed=seed,
                            step_s=protocol['channel_step_s'], ack_loss_prob=link['ack'])
    health = scene['health_observations'][0]
    health.update(soc_est=scene['initial_energy_Wh']/20, soc_lower=scene['initial_energy_Wh']/20,
                  energy_lower_Wh=scene['initial_energy_Wh'], model_version='synthetic-formal-v1-exact-initial',
                  uncertainty_method='synthetic_exact_initial_health')
    task_template = scene['tasks'][0]
    task_seed = int.from_bytes(hashlib.sha256(f'formal-tasks-v1|{seed}'.encode()).digest()[:8], 'big')
    rng = random.Random(task_seed)
    scene['tasks'] = []
    for index in range(protocol['task_counts'][cell['load_level']]):
        task = copy.deepcopy(task_template)
        task.update(task_id=f'T{index:02d}', arrival_s=0.0,
                    deadline_s=rng.choice(protocol['deadline_grid_s']),
                    priority_weight=rng.uniform(*protocol['priority_weight_range']),
                    payload_bytes=protocol['payload_bytes'], remaining_bytes=protocol['payload_bytes'])
        scene['tasks'].append(task)
    for key in ('true_windows', 'forecast_windows'):
        scene[key][0]['end_s'] = 26.0
        scene[key][0]['loss_profile'][0].update(robust_loss_prob=link['data_robust'], fast_loss_prob=link['data_fast'])
    config.update(kind='rule_validation', actions=[], evaluation_end_s=protocol['evaluation_end_s'], seed=seed)
    return RunConfig.model_validate(config).model_dump()


def _content_hash(config):
    scene = copy.deepcopy(config['scenario'])
    scene.pop('scenario_id')
    scene['channel'].pop('seed')
    return _hash(scene)


def materialize_inputs(protocol_path: Path, output: Path, *, excluded_seeds=(), excluded_content_hashes=()) -> dict:
    protocol = _read(protocol_path)
    _assert_loaded_code()
    _validate_protocol(protocol)
    if {row['seed'] for row in protocol['trajectories']} & set(excluded_seeds):
        raise ValueError('Training seed collision')
    if output.exists():
        raise ValueError('Output must be new')
    source_hashes = _source_hashes()
    template = _read(ROOT/'configs/scenarios/r3_normal.json')
    cells = {cell['cell_id']: cell for cell in protocol['cells']}
    rows, configs, seen = [], {}, set(excluded_content_hashes)
    for trace in protocol['trajectories']:
        config = _config(protocol, cells[trace['cell_id']], trace, template)
        content_hash = _content_hash(config)
        if content_hash in seen:
            raise ValueError('Input content collision')
        seen.add(content_hash)
        path = 'configs/'+trace['trajectory_id']+'.json'
        configs[path] = config
        rows.append(dict(**trace, config_path=path, config_sha256=_hash(config),
                         input_hash=_hash(config['scenario']), content_hash=content_hash))
    manifest = dict(schema_version='formal-input-manifest-v1', status='candidate_pending_review',
                    model=None, leakage_review='pending_A_N4b_delivery',
                    protocol_sha256=_hash(protocol), source_sha256=source_hashes, trajectories=rows)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.formal-inputs-', dir=output.parent))
    try:
        (staging/'configs').mkdir()
        for name, config in configs.items():
            (staging/name).write_bytes(_json_bytes(config))
        (staging/'protocol.json').write_bytes(_json_bytes(protocol))
        (staging/'manifest.json').write_bytes(_json_bytes(manifest))
        verify_inputs(staging/'manifest.json')
        if source_hashes != _source_hashes():
            raise ValueError('Generator source changed during publication')
        staging.rename(output)
    finally:
        if staging.exists():
            if staging.resolve().parent != output.parent.resolve() or not staging.name.startswith('.formal-inputs-'):
                raise ValueError('Unsafe staging cleanup path')
            shutil.rmtree(staging)
    return manifest


def verify_inputs(manifest_path: Path, *, require_frozen=False) -> dict:
    _assert_loaded_code()
    manifest = _read(manifest_path)
    root = manifest_path.parent
    protocol = _read(root/'protocol.json')
    _validate_protocol(protocol)
    required = {'schema_version', 'status', 'model', 'leakage_review', 'protocol_sha256', 'source_sha256', 'trajectories'}
    if (set(manifest) != required or manifest['schema_version'] != 'formal-input-manifest-v1'
            or manifest['leakage_review'] != 'pending_A_N4b_delivery'
            or manifest['status'] != 'candidate_pending_review' or manifest['model'] is not None):
        raise ValueError('Unsupported manifest status or model')
    if require_frozen:
        raise ValueError('Model and receiver review pending')
    if (manifest.get('protocol_sha256') != hashlib.sha256((root/'protocol.json').read_bytes()).hexdigest()
            or manifest.get('protocol_sha256') != _hash(protocol)
            or manifest.get('source_sha256') != _source_hashes()):
        raise ValueError('Protocol or generator hash mismatch')
    rows = manifest.get('trajectories', [])
    if len(rows) != 180:
        raise ValueError('Expected 180 trajectories')
    configs_root = root/'configs'
    if (configs_root.resolve() != root.resolve()/'configs'
            or {p.name for p in configs_root.iterdir()} != {t['trajectory_id']+'.json' for t in protocol['trajectories']}):
        raise ValueError('Config directory must contain exactly the advertised local files')
    template = _read(ROOT/'configs/scenarios/r3_normal.json')
    cells = {cell['cell_id']: cell for cell in protocol['cells']}
    seen = set()
    for trace, row in zip(protocol['trajectories'], rows):
        expected_path = 'configs/'+trace['trajectory_id']+'.json'
        if row.get('config_path') != expected_path:
            raise ValueError('Unexpected config path')
        config = _config(protocol, cells[trace['cell_id']], trace, template)
        expected = dict(**trace, config_path=expected_path, config_sha256=_hash(config),
                        input_hash=_hash(config['scenario']), content_hash=_content_hash(config))
        if row != expected or (root/expected_path).is_symlink():
            raise ValueError('Input record mismatch')
        if hashlib.sha256((root/expected_path).read_bytes()).hexdigest() != expected['config_sha256']:
            raise ValueError('Config hash mismatch')
        if row['content_hash'] in seen:
            raise ValueError('Duplicate input content')
        seen.add(row['content_hash'])
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', type=Path, default=ROOT/'experiments/formal_v1/protocol.json')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--verify', type=Path)
    args = parser.parse_args()
    if (args.output is None) == (args.verify is None):
        parser.error('Choose --output or --verify')
    result = verify_inputs(args.verify) if args.verify else materialize_inputs(args.protocol, args.output)
    print(json.dumps(dict(status=result['status'], trajectory_count=len(result['trajectories']))))


_IMPORT_HASHES = _source_hashes()


if __name__ == '__main__':
    main()
