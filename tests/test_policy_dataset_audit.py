"""Auditable label-quality and support coverage for A's frozen policy data."""

from __future__ import annotations

import json

import pytest

from training.audit_policy_dataset import (
    audit_frozen_dataset,
    audit_rows,
    main,
    render_markdown,
    write_audit_outputs,
)


def _row(
    sample_id: str,
    *,
    energy_wh: float,
    deadline_s: float,
    window_start_s: float | None,
    scores: tuple[tuple[str, float, bool], ...],
    elapsed_ms: float,
    solver_status: str = "OPTIMAL",
) -> dict[str, object]:
    windows = [] if window_start_s is None else [{"start_s": window_start_s}]
    return {
        "sample_id": sample_id,
        "solver_status": solver_status,
        "elapsed_ms": elapsed_ms,
        "observation": {
            "health": {"energy_lower_Wh": energy_wh},
            "forecast_windows": windows,
            "tasks": [{"task_id": "T1", "deadline_s": deadline_s}],
        },
        "candidate_scores": [
            {
                "task_id": None if mode == "idle" else "T1",
                "mode": mode,
                "score": score,
                "feasible": feasible,
            }
            for mode, score, feasible in scores
        ],
    }


def test_audit_rows_separates_label_quality_from_support_coverage():
    rows = [
        _row(
            "deadline_low_energy",
            energy_wh=0.4,
            deadline_s=1.0,
            window_start_s=2.0,
            scores=(("robust", 0.5, True), ("fast", 0.0, False), ("idle", 0.0, True)),
            elapsed_ms=1.0,
        ),
        _row(
            "no_window_idle_only",
            energy_wh=1.0,
            deadline_s=5.0,
            window_start_s=None,
            scores=(("robust", 0.0, False), ("fast", 0.0, False), ("idle", 1.0, True)),
            elapsed_ms=2.0,
        ),
        _row(
            "tied_idle",
            energy_wh=2.0,
            deadline_s=5.0,
            window_start_s=0.0,
            scores=(("robust", 1.0, True), ("fast", 0.5, True), ("idle", 1.0, True)),
            elapsed_ms=3.0,
            solver_status="TIME_LIMIT_FEASIBLE",
        ),
    ]

    audit = audit_rows(rows, reserve_wh=0.5)

    assert audit["observation_count"] == 3
    assert audit["label_quality"] == {
        "task_action_all_zero": {"count": 1, "fraction": pytest.approx(1 / 3)},
        "idle_in_optimal_set": {"count": 2, "fraction": pytest.approx(2 / 3)},
        "tied_optimal_set": {"count": 1, "fraction": pytest.approx(1 / 3)},
        "unique_non_idle_best": {"count": 1, "fraction": pytest.approx(1 / 3)},
        "optimal_set_size_counts": {"1": 2, "2": 1},
        "feasible_top_two_margin": {
            "defined_count": 2,
            "undefined_count": 1,
            "zero_count": 1,
            "min": 0.0,
            "mean": 0.25,
            "median": 0.25,
            "p95_nearest_rank": 0.5,
            "max": 0.5,
        },
    }
    assert audit["coverage"] == {
        "low_energy_at_or_below_reserve": {"count": 1, "fraction": pytest.approx(1 / 3), "reserve_Wh": 0.5},
        "no_forecast_window": {"count": 1, "fraction": pytest.approx(1 / 3)},
        "deadline_before_or_at_first_window": {"count": 1, "fraction": pytest.approx(1 / 3)},
        "all_task_actions_infeasible": {"count": 1, "fraction": pytest.approx(1 / 3)},
        "any_task_without_feasible_mode": {"count": 1, "fraction": pytest.approx(1 / 3)},
    }
    assert audit["teacher"] == {
        "solver_status_counts": {"OPTIMAL": 2, "TIME_LIMIT_FEASIBLE": 1},
        "elapsed_ms": {
            "count": 3,
            "min": 1.0,
            "mean": 2.0,
            "median": 2.0,
            "p95_nearest_rank": 3.0,
            "max": 3.0,
        },
    }


def test_frozen_a_n3_v2_audit_records_current_label_imbalance_and_missing_edges():
    audit = audit_frozen_dataset()

    assert audit["inputs"]["samples_sha256"] == (
        "2df964e78a6bf6220b4c48c92b29f4838d01af13281f41f666a306e96c5b8957"
    )
    assert audit["observation_count"] == 20
    assert audit["label_quality"]["task_action_all_zero"]["count"] == 13
    assert audit["label_quality"]["idle_in_optimal_set"]["count"] == 19
    assert audit["label_quality"]["tied_optimal_set"]["count"] == 6
    assert audit["label_quality"]["unique_non_idle_best"]["count"] == 1
    assert audit["coverage"]["low_energy_at_or_below_reserve"]["count"] == 0
    assert audit["coverage"]["no_forecast_window"]["count"] == 0
    assert audit["coverage"]["deadline_before_or_at_first_window"]["count"] == 0
    assert audit["coverage"]["all_task_actions_infeasible"]["count"] == 13
    assert audit["teacher"]["solver_status_counts"] == {"OPTIMAL": 20}


def test_audit_outputs_are_deterministic_idempotent_and_explicit_about_limits(tmp_path):
    audit = audit_frozen_dataset()
    output = tmp_path / "audit"

    paths = write_audit_outputs(audit, output)
    first_json = paths["json"].read_bytes()
    first_markdown = paths["markdown"].read_bytes()
    repeated = write_audit_outputs(audit, output)

    assert repeated == paths
    assert paths["json"].read_bytes() == first_json
    assert paths["markdown"].read_bytes() == first_markdown
    assert json.loads(first_json) == audit
    markdown = render_markdown(audit)
    assert first_markdown.decode("utf-8") == markdown
    assert "13/20" in markdown
    assert "19/20" in markdown
    assert "0/20" in markdown
    assert "冻结记录中的教师运行元数据" in markdown
    assert "不构成新实验结果" in markdown
    assert "不能证明 learned 优于规则策略" in markdown


def test_audit_output_refuses_to_overwrite_different_evidence(tmp_path):
    output = tmp_path / "audit"
    output.mkdir()
    (output / "audit.json").write_text("different\n", encoding="utf-8")

    with pytest.raises(FileExistsError, match="audit.json"):
        write_audit_outputs(audit_frozen_dataset(), output)


def test_cli_writes_frozen_audit_package(tmp_path):
    output = tmp_path / "cli-audit"

    assert main(["--output-dir", str(output)]) == 0
    assert (output / "audit.json").is_file()
    assert (output / "README.md").is_file()
