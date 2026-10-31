"""Build 20 independent synthetic public Observations for H02 v2 review."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import tempfile

from backend.contracts import Observation
from training.generate_teacher_data import canonical_json


SOURCE_COUNT = 20
FORECAST_VERSION = "h02-v2-synthetic-v1"


def _build_observation(index: int) -> dict[str, object]:
    task_count = 1 + index % 3
    tasks = []
    for task_index in range(task_count):
        payload_bytes = 1024 * (1 + (index + task_index) % 2)
        tasks.append({
            "task_id": f"T{task_index + 1}",
            "arrival_s": 0.0,
            "deadline_s": float(4 + index % 5 + task_index * 2),
            "payload_bytes": payload_bytes,
            "remaining_bytes": payload_bytes,
            "priority_weight": float(1 + (index * 2 + task_index) % 5),
            "business_class": "synthetic",
            "data_location": "satellite_1",
        })

    window_start = float(index % 3)
    robust_bps = float(4096 + 1024 * (index % 7))
    soc_lower = round(0.05 + 0.03 * index, 2)
    observation = {
        "schema_version": "1.0",
        "run_id": f"h02_v2_run_{index:02d}",
        "policy_id": "teacher",
        "sim_time_s": 0.0,
        "tasks": tasks,
        "forecast_windows": [{
            "window_id": "W1",
            "start_s": window_start,
            "end_s": float(30 + index % 5 * 6),
            "rate_profile": [{
                "time_s": window_start,
                "robust_bps": robust_bps,
                "fast_bps": robust_bps * 2,
            }],
            "loss_profile": [{
                "time_s": window_start,
                "robust_loss_prob": 0.0,
                "fast_loss_prob": 0.0,
            }],
            "source": "synthetic",
            "forecast_version": FORECAST_VERSION,
        }],
        "health": {
            "soc_est": round(soc_lower + 0.05, 2),
            "soc_lower": soc_lower,
            "capacity_Wh_est": 20.0,
            "capacity_lower_Wh": 20.0,
            "energy_lower_Wh": soc_lower * 20.0,
            "rul_est": None,
            "rul_unit": None,
            "uncertainty_method": "synthetic_fixed_bounds",
            "model_version": "synthetic-h02-v2",
            "observed_at_s": 0.0,
            "available_at_s": 0.0,
            "reason_codes": ["RUL_UNAVAILABLE"],
        },
        "inflight": None,
        "cache_bytes": sum(task["remaining_bytes"] for task in tasks),
        "forecast_version": FORECAST_VERSION,
    }
    return Observation.model_validate(observation).model_dump(mode="json")


def build_source_rows() -> list[dict[str, object]]:
    return [{
        "sample_id": f"h02_v2_{index:02d}",
        "source_group_id": f"h02-v2-source-{index:02d}",
        "observation": _build_observation(index),
    } for index in range(SOURCE_COUNT)]


def write_source(output_path: Path) -> None:
    output_path = Path(output_path)
    content = ("".join(canonical_json(row) + "\n" for row in build_source_rows())
               .encode("utf-8"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        if output_path.read_bytes() != content:
            raise ValueError("Refusing to overwrite differing source")
        return

    fd, temporary = tempfile.mkstemp(prefix=".h02-v2-source-", dir=output_path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, output_path)
        except FileExistsError:
            if output_path.read_bytes() != content:
                raise ValueError("Refusing to overwrite differing source")
    finally:
        os.unlink(temporary)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        write_source(args.output)
    except (OSError, ValueError) as error:
        print(str(error))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
