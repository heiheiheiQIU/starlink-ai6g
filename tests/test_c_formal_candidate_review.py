from copy import deepcopy

import pytest


def candidate():
    rows = []
    for cell in range(18):
        for offset in range(10):
            index = cell * 10 + offset
            rows.append({
                "trajectory_id": f"formal_v2_{index:03d}",
                "cell_id": f"cell_{cell:02d}",
                "seed": 600000 + index,
                "config_path": f"configs/formal_v2_{index:03d}.json",
                "config_sha256": f"config-{index:03d}",
                "input_hash": f"input-{index:03d}",
                "content_hash": f"content-{index:03d}",
            })
    receipts = {
        role: {"role": role, "reviewer": f"member-{role}", "status": "accepted"}
        for role in "ABC"
    }
    return {"trajectories": rows, "generation_receipts": receipts}


def test_summary_keeps_machine_verification_separate_from_human_authorization():
    from scripts.review_formal_v2_candidate_c import summarize_verified_candidate

    summary = summarize_verified_candidate(candidate(), "a" * 64)

    assert summary["status"] == "machine_verified_human_pending"
    assert summary["trajectory_count"] == 180
    assert summary["cell_count"] == 18
    assert summary["trajectories_per_cell"] == 10
    assert summary["seed_range"] == [600000, 600179]
    assert summary["unique_counts"] == {
        "trajectory_id": 180,
        "seed": 180,
        "config_sha256": 180,
        "input_hash": 180,
        "content_hash": 180,
    }
    assert summary["formal_runs_authorized"] is False
    assert summary["human_review_required"] is True


@pytest.mark.parametrize("field", [
    "trajectory_id", "seed", "config_sha256", "input_hash", "content_hash",
])
def test_summary_rejects_duplicate_candidate_identity_or_hash(field):
    from scripts.review_formal_v2_candidate_c import summarize_verified_candidate

    value = candidate()
    value["trajectories"][1][field] = value["trajectories"][0][field]

    with pytest.raises(ValueError, match="unique"):
        summarize_verified_candidate(value, "a" * 64)


def test_summary_rejects_wrong_seed_range_and_cell_population():
    from scripts.review_formal_v2_candidate_c import summarize_verified_candidate

    wrong_seed = candidate()
    wrong_seed["trajectories"][-1]["seed"] = 700000
    with pytest.raises(ValueError, match="seed range"):
        summarize_verified_candidate(wrong_seed, "a" * 64)

    wrong_cell = deepcopy(candidate())
    wrong_cell["trajectories"][-1]["cell_id"] = "cell_00"
    with pytest.raises(ValueError, match="18 cells"):
        summarize_verified_candidate(wrong_cell, "a" * 64)
