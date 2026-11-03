"""Deterministic audit of frozen policy labels and support coverage."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, median

from training.policy_dataset import DEFAULT_CONFIG, PolicyDataError, load_frozen_dataset


ROOT = Path(__file__).resolve().parents[1]


def _fraction(count: int, total: int) -> dict[str, int | float]:
    return {"count": count, "fraction": count / total}


def _distribution(values: list[float]) -> dict[str, int | float]:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("Cannot summarize an empty distribution")
    p95_index = math.ceil(0.95 * len(ordered)) - 1
    return {
        "count": len(ordered),
        "min": ordered[0],
        "mean": mean(ordered),
        "median": median(ordered),
        "p95_nearest_rank": ordered[p95_index],
        "max": ordered[-1],
    }


def _number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field} must be finite")
    return result


def audit_rows(
    rows: list[dict[str, object]], *, reserve_wh: float
) -> dict[str, object]:
    """Summarize labels separately from observable support predicates.

    A task-action label is any non-idle candidate. Optimal-set and margin
    calculations use feasible candidates only. The deadline predicate is
    deliberately narrow: at least one visible task has a deadline no later
    than the first forecast-window start. It is coverage evidence, not a
    causal diagnosis of teacher infeasibility.
    """

    reserve = _number(reserve_wh, "reserve_wh")
    if reserve < 0.0:
        raise ValueError("reserve_wh must be non-negative")
    if not rows:
        raise ValueError("At least one audit row is required")

    task_action_all_zero = 0
    idle_in_optimal_set = 0
    tied_optimal_set = 0
    unique_non_idle_best = 0
    optimal_set_sizes: Counter[int] = Counter()
    margins: list[float] = []

    low_energy = 0
    no_window = 0
    deadline_before_window = 0
    all_task_actions_infeasible = 0
    any_task_without_feasible_mode = 0

    statuses: Counter[str] = Counter()
    elapsed_values: list[float] = []

    for row in rows:
        labels = row.get("candidate_scores")
        observation = row.get("observation")
        if not isinstance(labels, list) or not isinstance(observation, dict):
            raise ValueError("Each row requires candidate_scores and observation")

        parsed: list[tuple[object, str, float, bool]] = []
        for label in labels:
            if not isinstance(label, dict):
                raise ValueError("Candidate labels must be objects")
            mode = label.get("mode")
            feasible = label.get("feasible")
            if not isinstance(mode, str) or type(feasible) is not bool:
                raise ValueError("Candidate mode and feasibility are invalid")
            parsed.append(
                (
                    label.get("task_id"),
                    mode,
                    _number(label.get("score"), "candidate score"),
                    feasible,
                )
            )

        feasible_labels = [label for label in parsed if label[3]]
        if not feasible_labels:
            raise ValueError("Each row requires at least one feasible candidate")
        task_labels = [label for label in parsed if label[1] != "idle"]
        idle_labels = [label for label in parsed if label[1] == "idle"]
        if len(idle_labels) != 1:
            raise ValueError("Each row requires exactly one idle candidate")

        if task_labels and all(label[2] == 0.0 for label in task_labels):
            task_action_all_zero += 1
        best_score = max(label[2] for label in feasible_labels)
        optimal = [label for label in feasible_labels if label[2] == best_score]
        optimal_set_sizes[len(optimal)] += 1
        if len(optimal) > 1:
            tied_optimal_set += 1
        if any(label[1] == "idle" for label in optimal):
            idle_in_optimal_set += 1
        if len(optimal) == 1 and optimal[0][1] != "idle":
            unique_non_idle_best += 1

        ordered_scores = sorted((label[2] for label in feasible_labels), reverse=True)
        if len(ordered_scores) >= 2:
            margins.append(ordered_scores[0] - ordered_scores[1])

        health = observation.get("health")
        windows = observation.get("forecast_windows")
        tasks = observation.get("tasks")
        if not isinstance(health, dict) or not isinstance(windows, list) or not isinstance(tasks, list):
            raise ValueError("Observation audit fields are invalid")
        energy = _number(health.get("energy_lower_Wh"), "energy_lower_Wh")
        low_energy += int(energy <= reserve)
        if not windows:
            no_window += 1
        else:
            starts = [
                _number(window.get("start_s"), "window start_s")
                for window in windows
                if isinstance(window, dict)
            ]
            if len(starts) != len(windows):
                raise ValueError("Forecast windows must be objects")
            first_start = min(starts)
            deadline_before_window += int(
                any(
                    isinstance(task, dict)
                    and _number(task.get("deadline_s"), "task deadline_s") <= first_start
                    for task in tasks
                )
            )

        all_task_actions_infeasible += int(
            bool(task_labels) and not any(label[3] for label in task_labels)
        )
        by_task: dict[object, list[tuple[object, str, float, bool]]] = {}
        for label in task_labels:
            by_task.setdefault(label[0], []).append(label)
        any_task_without_feasible_mode += int(
            bool(by_task)
            and any(not any(label[3] for label in candidates) for candidates in by_task.values())
        )

        status = row.get("solver_status")
        if not isinstance(status, str) or not status:
            raise ValueError("solver_status must be a non-empty string")
        statuses[status] += 1
        elapsed_values.append(_number(row.get("elapsed_ms"), "elapsed_ms"))

    total = len(rows)
    margin_summary: dict[str, int | float | None] = {
        "defined_count": len(margins),
        "undefined_count": total - len(margins),
        "zero_count": sum(value == 0.0 for value in margins),
        "min": None,
        "mean": None,
        "median": None,
        "p95_nearest_rank": None,
        "max": None,
    }
    if margins:
        margin_summary.update({key: value for key, value in _distribution(margins).items() if key != "count"})

    return {
        "schema_version": "policy-dataset-audit-v1",
        "observation_count": total,
        "label_quality": {
            "task_action_all_zero": _fraction(task_action_all_zero, total),
            "idle_in_optimal_set": _fraction(idle_in_optimal_set, total),
            "tied_optimal_set": _fraction(tied_optimal_set, total),
            "unique_non_idle_best": _fraction(unique_non_idle_best, total),
            "optimal_set_size_counts": {
                str(size): optimal_set_sizes[size] for size in sorted(optimal_set_sizes)
            },
            "feasible_top_two_margin": margin_summary,
        },
        "coverage": {
            "low_energy_at_or_below_reserve": {
                **_fraction(low_energy, total),
                "reserve_Wh": reserve,
            },
            "no_forecast_window": _fraction(no_window, total),
            "deadline_before_or_at_first_window": _fraction(deadline_before_window, total),
            "all_task_actions_infeasible": _fraction(all_task_actions_infeasible, total),
            "any_task_without_feasible_mode": _fraction(any_task_without_feasible_mode, total),
        },
        "teacher": {
            "solver_status_counts": {key: statuses[key] for key in sorted(statuses)},
            "elapsed_ms": _distribution(elapsed_values),
        },
    }


def _read_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected object in {path}")
    return value


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit_frozen_dataset(
    config_path: Path = DEFAULT_CONFIG, *, root: Path = ROOT
) -> dict[str, object]:
    """Verify and audit the frozen A-N3 v2 dataset without changing it."""

    config_path = Path(config_path)
    root = Path(root)
    frozen = load_frozen_dataset(config_path, root=root)
    config = _read_json(config_path)
    samples_path = root / str(config["dataset_path"])
    manifest_path = root / str(config["dataset_manifest_path"])
    manifest = _read_json(manifest_path)
    teacher_config_path = root / "configs/teacher.json"
    teacher_config = _read_json(teacher_config_path)
    teacher_hash = _sha256(teacher_config_path)
    if manifest.get("teacher_config_sha256") != teacher_hash:
        raise PolicyDataError("TEACHER_CONFIG_HASH", "Frozen labels use another teacher config")

    rows = [json.loads(line) for line in samples_path.read_text(encoding="utf-8").splitlines() if line]
    audit = audit_rows(rows, reserve_wh=float(teacher_config["policy"]["reserve_Wh"]))
    audit["inputs"] = {
        "dataset_path": samples_path.relative_to(root).as_posix(),
        "dataset_version": manifest.get("dataset_version"),
        "source_revision": manifest.get("source_revision"),
        "samples_sha256": frozen.samples_sha256,
        "split_sha256": frozen.split_sha256,
        "teacher_version": manifest.get("teacher_version"),
        "teacher_config_sha256": teacher_hash,
    }
    return audit


def render_markdown(audit: dict[str, object]) -> str:
    inputs = audit["inputs"]
    quality = audit["label_quality"]
    coverage = audit["coverage"]
    teacher = audit["teacher"]
    total = audit["observation_count"]

    def count_line(name: str, value: dict[str, object]) -> str:
        count = value["count"]
        percent = 100.0 * float(value["fraction"])
        return f"- {name}：`{count}/{total}`（`{percent:.1f}%`）。"

    margin = quality["feasible_top_two_margin"]
    elapsed = teacher["elapsed_ms"]
    lines = [
        "# A-N4 冻结教师数据审计",
        "",
        "## 输入绑定",
        "",
        f"- 数据集：`{inputs['dataset_version']}`；`{inputs['dataset_path']}`。",
        f"- 样本 SHA256：`{inputs['samples_sha256']}`。",
        f"- 划分 SHA256：`{inputs['split_sha256']}`。",
        f"- 教师：`{inputs['teacher_version']}`；配置 SHA256：`{inputs['teacher_config_sha256']}`。",
        "",
        "## 标签辨识度",
        "",
        count_line("任务动作标签全部为零", quality["task_action_all_zero"]),
        count_line("idle 位于可行最优集合", quality["idle_in_optimal_set"]),
        count_line("可行最优集合存在并列", quality["tied_optimal_set"]),
        count_line("唯一最优是非 idle 动作", quality["unique_non_idle_best"]),
        (
            "- 可行候选前两名优势差："
            f"有定义 `{margin['defined_count']}` 条、无定义 `{margin['undefined_count']}` 条、"
            f"零优势 `{margin['zero_count']}` 条；中位数 `{margin['median']}`，"
            f"P95（nearest-rank）`{margin['p95_nearest_rank']}`。"
        ),
        "",
        "## 支持域覆盖",
        "",
        count_line(
            f"公开能量下界不高于 reserve={coverage['low_energy_at_or_below_reserve']['reserve_Wh']} Wh",
            coverage["low_energy_at_or_below_reserve"],
        ),
        count_line("没有预测窗口", coverage["no_forecast_window"]),
        count_line("至少一个期限早于或等于首个窗口开始", coverage["deadline_before_or_at_first_window"]),
        count_line("全部任务动作不可行", coverage["all_task_actions_infeasible"]),
        count_line("至少一个任务没有可行模式", coverage["any_task_without_feasible_mode"]),
        "",
        "上述覆盖谓词只描述公开 Observation 与标签，不把不可行性归因于单一物理原因。",
        "",
        "## 冻结记录中的教师运行元数据",
        "",
        "以下状态与耗时直接读取冻结样本，不是本轮重新求解所得。",
        "",
        f"- 状态计数：`{json.dumps(teacher['solver_status_counts'], ensure_ascii=False, sort_keys=True)}`。",
        (
            f"- 耗时（ms）：最小 `{elapsed['min']}`，均值 `{elapsed['mean']}`，"
            f"中位数 `{elapsed['median']}`，P95 `{elapsed['p95_nearest_rank']}`，"
            f"最大 `{elapsed['max']}`。"
        ),
        "",
        "## 结论边界",
        "",
        "本文件是对既有冻结 20 条合成教师数据的审计，不构成新实验结果，也没有修改冻结样本。",
        "当前数据可继续用于管线、哈希和小样本拟合回归，但不能证明 learned 优于规则策略。",
        "扩样应补充独立来源的低能量、无窗口和期限冲突状态，并在来源分组后再划分数据集。",
        "",
    ]
    return "\n".join(lines)


def write_audit_outputs(audit: dict[str, object], output_dir: Path) -> dict[str, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": output_dir / "audit.json",
        "markdown": output_dir / "README.md",
    }
    contents = {
        "json": (
            json.dumps(audit, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
        ).encode("utf-8"),
        "markdown": render_markdown(audit).encode("utf-8"),
    }
    for name, path in paths.items():
        content = contents[name]
        if path.exists():
            if path.read_bytes() != content:
                raise FileExistsError(f"Refusing to overwrite different {path.name}")
            continue
        path.write_bytes(content)
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    config = args.config if args.config.is_absolute() else root / args.config
    audit = audit_frozen_dataset(config, root=root)
    write_audit_outputs(audit, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
