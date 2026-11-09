"""Verify a formal-v2 candidate package and emit a non-authorizing C review summary."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from backend.formal_freeze import file_hash, verify_candidate


IDENTITY_FIELDS = (
    "trajectory_id",
    "seed",
    "config_sha256",
    "input_hash",
    "content_hash",
)
EXPECTED_SEEDS = set(range(600000, 600180))
SHA256 = re.compile(r"[0-9a-f]{64}")


def summarize_verified_candidate(candidate: dict, manifest_sha256: str) -> dict:
    rows = candidate.get("trajectories")
    if not isinstance(rows, list) or len(rows) != 180:
        raise ValueError("Expected exactly 180 candidate trajectories")
    if not isinstance(manifest_sha256, str) or SHA256.fullmatch(manifest_sha256) is None:
        raise ValueError("Invalid candidate manifest SHA256")

    unique_counts = {}
    for field in IDENTITY_FIELDS:
        try:
            unique_counts[field] = len({row[field] for row in rows})
        except (KeyError, TypeError) as error:
            raise ValueError(f"Missing candidate identity field: {field}") from error
        if unique_counts[field] != 180:
            raise ValueError(f"Candidate {field} values must be unique")

    seeds = {row["seed"] for row in rows}
    if seeds != EXPECTED_SEEDS:
        raise ValueError("Candidate seed range must be exactly 600000-600179")

    cell_counts = Counter(row.get("cell_id") for row in rows)
    if len(cell_counts) != 18 or set(cell_counts.values()) != {10} or None in cell_counts:
        raise ValueError("Expected 18 cells with 10 trajectories each")

    receipts = candidate.get("generation_receipts")
    if not isinstance(receipts, dict) or set(receipts) != set("ABC"):
        raise ValueError("Expected A/B/C generation receipts")
    receipt_summary = {}
    reviewers = set()
    for role in "ABC":
        receipt = receipts[role]
        reviewer = receipt.get("reviewer")
        if receipt.get("role") != role or receipt.get("status") != "accepted" or not reviewer:
            raise ValueError(f"Invalid generation receipt for {role}")
        reviewers.add(reviewer)
        receipt_summary[role] = {"status": "accepted", "reviewer": reviewer}
    if len(reviewers) != 3:
        raise ValueError("Generation receipts require three independent reviewers")

    return {
        "schema_version": "c-formal-v2-candidate-review-v1",
        "status": "machine_verified_human_pending",
        "candidate_manifest_sha256": manifest_sha256,
        "trajectory_count": 180,
        "cell_count": 18,
        "trajectories_per_cell": 10,
        "seed_range": [600000, 600179],
        "policy_ids": ["edf", "value", "learned"],
        "unique_counts": unique_counts,
        "generation_receipts": receipt_summary,
        "human_review_required": True,
        "formal_runs_authorized": False,
        "next_gate": "A/B/C post-generation candidate and leakage review",
    }


def review_candidate(manifest_path: Path) -> dict:
    manifest_path = Path(manifest_path)
    candidate = verify_candidate(manifest_path)
    return summarize_verified_candidate(candidate, file_hash(manifest_path))


def write_review(manifest_path: Path, output_path: Path) -> dict:
    output_path = Path(output_path)
    if output_path.exists():
        raise ValueError("Review output must be new")
    summary = review_candidate(manifest_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = write_review(args.manifest, args.output)
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
