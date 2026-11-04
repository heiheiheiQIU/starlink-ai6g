import copy
import hashlib
import json
from pathlib import Path

from backend.contracts import Action
from backend.simulator.engine import ScenarioConfig

ROOT = Path(__file__).resolve().parents[1]
DATASET_VERSION = "a-n4-pilot-v1"
SOURCE_COUNT = 30
SOURCE_SEED_START = 410000
DEFAULT_SPLIT_SEED = 20261104
DEFAULT_SPLIT_COUNTS = (18, 6, 6)
IDLE = Action(
    task_id=None, mode="idle", scheduled_bytes=0,
    reason_codes=[], fallback=False,
).model_dump(mode="json")

def canonical_json(value: object) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False,
    )

def sha256_json(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()

def _window(window_id: str, start_s: float, end_s: float) -> dict[str, object]:
    return {
        "window_id": window_id,
        "start_s": start_s,
        "end_s": end_s,
        "rate_profile": [{
            "time_s": start_s,
            "robust_bps": 8192.0,
            "fast_bps": 16384.0,
        }],
        "loss_profile": [{
            "time_s": start_s,
            "robust_loss_prob": 0.0,
            "fast_loss_prob": 0.0,
        }],
        "source": "synthetic",
        "forecast_version": "a-n4-pilot-forecast-v1",
    }

def _task(index: int, variant: int) -> dict[str, object]:
    payload = (1 + ((variant + index) % 4)) * 1024
    return {
        "task_id": f"T{index:02d}",
        "arrival_s": 0.0 if index == 0 else float(2 * (index % 2)),
        "deadline_s": float(8 + 4 * ((variant + index) % 6)),
        "payload_bytes": payload,
        "remaining_bytes": payload,
        "priority_weight": 1.0 + 0.5 * ((variant + index) % 5),
        "business_class": "synthetic",
        "data_location": "satellite_1",
    }

def _source(
    source_id: str, seed: int, family: str, *,
    energy_wh: float,
    tasks: list[dict[str, object]],
    windows: list[dict[str, object]],
    partial: bool,
) -> dict[str, object]:
    template = json.loads(
        (ROOT / "configs/scenarios/r3_normal.json").read_text(encoding="utf-8")
    )["scenario"]
    scenario = copy.deepcopy(template)
    scenario.update({
        "scenario_id": source_id,
        "initial_energy_Wh": energy_wh,
        "forecast_version": "a-n4-pilot-forecast-v1",
        "tasks": tasks,
        "true_windows": copy.deepcopy(windows),
        "forecast_windows": copy.deepcopy(windows),
    })
    ratio = energy_wh / 20.0
    scenario["health_observations"] = [{
        "soc_est": ratio,
        "soc_lower": ratio,
        "capacity_Wh_est": 20.0,
        "capacity_lower_Wh": 20.0,
        "energy_lower_Wh": energy_wh,
        "rul_est": None,
        "rul_unit": None,
        "uncertainty_method": "synthetic_exact_pilot",
        "model_version": "synthetic-a-n4-pilot-v1",
        "observed_at_s": 0.0,
        "available_at_s": 0.0,
        "reason_codes": ["RUL_UNAVAILABLE"],
    }]
    parsed = ScenarioConfig.model_validate(scenario).model_dump(mode="json")
    if partial:
        send = Action(
            task_id="T00", mode="robust", scheduled_bytes=1024,
            reason_codes=[], fallback=False,
        ).model_dump(mode="json")
        evolution = [
            {"dt_s": 2.0, "action": send},
            {"dt_s": 2.0, "action": IDLE},
        ]
        capture = [0, 2]
    else:
        evolution = [
            {"dt_s": 2.0, "action": IDLE},
            {"dt_s": 2.0, "action": IDLE},
        ]
        capture = [0, 1, 2] if family == "decision" else [0, 1]
    identity = copy.deepcopy(parsed)
    identity.pop("scenario_id")
    if isinstance(identity.get("channel"), dict):
        identity["channel"].pop("seed", None)
    return {
        "source_id": source_id,
        "seed": seed,
        "family": family,
        "scenario": parsed,
        "evolution_steps": evolution,
        "capture_after_steps": capture,
        "content_sha256": sha256_json(identity),
    }

def build_sources() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index in range(24):
        count = 1 + index % 4
        tasks = [_task(task_index, index) for task_index in range(count)]
        partial = index % 4 == 0
        if partial:
            tasks[0] = {
                **tasks[0],
                "payload_bytes": 2048,
                "remaining_bytes": 2048,
            }
        windows = [
            _window(f"W{slot}", float(6 * slot), float(6 * slot + 6))
            for slot in range(1 + index % 3)
        ]
        rows.append(_source(
            f"decision_{index:02d}",
            SOURCE_SEED_START + index,
            "decision",
            energy_wh=(0.6, 1.2, 10.0)[index % 3],
            tasks=tasks,
            windows=windows,
            partial=partial,
        ))
    rows.extend([
        _source(
            "low_energy_00", 410024, "low_energy",
            energy_wh=0.49, tasks=[_task(0, 24)],
            windows=[_window("W0", 0.0, 6.0)], partial=False,
        ),
        _source(
            "low_energy_01", 410025, "low_energy",
            energy_wh=0.5309017777778, tasks=[_task(0, 25)],
            windows=[_window("W0", 0.0, 6.0)], partial=False,
        ),
        _source(
            "no_window_00", 410026, "no_window",
            energy_wh=1.2, tasks=[_task(0, 26)], windows=[], partial=False,
        ),
        _source(
            "no_window_01", 410027, "no_window",
            energy_wh=10.0, tasks=[_task(0, 27), _task(1, 27)],
            windows=[], partial=False,
        ),
        _source(
            "deadline_before_window_00", 410028, "deadline_before_window",
            energy_wh=1.2,
            tasks=[{**_task(0, 28), "deadline_s": 4.0}],
            windows=[_window("W0", 8.0, 14.0)], partial=False,
        ),
        _source(
            "deadline_before_window_01", 410029, "deadline_before_window",
            energy_wh=10.0,
            tasks=[{**_task(0, 29), "deadline_s": 6.0}],
            windows=[_window("W0", 10.0, 16.0)], partial=False,
        ),
    ])
    if len(rows) != SOURCE_COUNT:
        raise AssertionError("Pilot source count changed")
    return rows

def build_source_splits(
    sources: list[dict[str, object]], *,
    split_seed: int,
    counts: tuple[int, int, int],
) -> dict[str, object]:
    ordered = sorted(
        (str(row["source_id"]) for row in sources),
        key=lambda source_id: hashlib.sha256(
            f"{split_seed}:{source_id}".encode("utf-8")
        ).hexdigest(),
    )
    train, validation, test = counts
    if len(ordered) != sum(counts) or len(set(ordered)) != len(ordered):
        raise ValueError("Source IDs and split counts do not match")
    return {
        "schema_version": "pilot-source-splits-v1",
        "dataset_version": DATASET_VERSION,
        "split_seed": split_seed,
        "counts": {"train": train, "validation": validation, "test": test},
        "splits": {
            "train": ordered[:train],
            "validation": ordered[train:train + validation],
            "test": ordered[train + validation:],
        },
    }

def write_source_protocol(
    output_dir: Path, *, split_seed: int = DEFAULT_SPLIT_SEED
) -> dict[str, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        raise ValueError("Source protocol output must be empty")
    sources = build_sources()
    splits = build_source_splits(
        sources, split_seed=split_seed, counts=DEFAULT_SPLIT_COUNTS
    )
    paths = {
        "sources": output_dir / "sources.jsonl",
        "splits": output_dir / "source_splits.json",
    }
    paths["sources"].write_text(
        "".join(canonical_json(row) + "\n" for row in sources),
        encoding="utf-8", newline="\n",
    )
    paths["splits"].write_text(
        canonical_json(splits) + "\n", encoding="utf-8", newline="\n"
    )
    return paths
