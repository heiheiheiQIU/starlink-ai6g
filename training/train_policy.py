"""Deterministic small-sample trainer for the A-N3 candidate scorer."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import io
import json
import os
from pathlib import Path
import random
import subprocess
import zipfile

import numpy as np
import torch
from torch import nn
from torch.nn import functional as F

from training.policy_dataset import (
    FrozenPolicyDataset,
    Normalization,
    load_frozen_dataset,
    normalise_example,
)


ROOT = Path(__file__).resolve().parents[1]
WEIGHT_NAMES = {
    "layer1.weight": "layer1_weight",
    "layer1.bias": "layer1_bias",
    "layer2.weight": "layer2_weight",
    "layer2.bias": "layer2_bias",
    "utility.weight": "utility_weight",
    "utility.bias": "utility_bias",
    "feasibility.weight": "feasibility_weight",
    "feasibility.bias": "feasibility_bias",
}


class CandidateMLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.layer1 = nn.Linear(23, 32)
        self.layer2 = nn.Linear(32, 16)
        self.utility = nn.Linear(16, 1)
        self.feasibility = nn.Linear(16, 1)

    def forward(self, values):
        hidden = torch.relu(self.layer1(values))
        hidden = torch.relu(self.layer2(hidden))
        return torch.sigmoid(self.utility(hidden)).squeeze(-1), self.feasibility(hidden).squeeze(-1)


@dataclass(frozen=True)
class TrainingResult:
    seed: int
    state_dict: dict[str, torch.Tensor]
    metrics: dict[str, dict[str, float | int]]


def _seed_everything(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(1)


def _tensors(dataset: FrozenPolicyDataset, split: str):
    rows = dataset.splits[split]
    inputs = []
    scores = []
    feasible = []
    weights = []
    for example in rows:
        encoded = normalise_example(example, dataset.normalization)
        inputs.extend(encoded)
        scores.extend(example.target_scores)
        feasible.extend(float(value) for value in example.target_feasible)
        weights.extend([1.0 / (len(rows) * len(encoded))] * len(encoded))
    return (
        torch.tensor(inputs, dtype=torch.float32),
        torch.tensor(scores, dtype=torch.float32),
        torch.tensor(feasible, dtype=torch.float32),
        torch.tensor(weights, dtype=torch.float32),
    )


def _loss(model, batch, feasibility_loss_weight: float):
    inputs, target_scores, target_feasible, weights = batch
    utility, feasibility_logits = model(inputs)
    utility_bce = torch.sum(
        weights * F.binary_cross_entropy(utility, target_scores, reduction="none")
    )
    feasibility_bce = torch.sum(
        weights
        * F.binary_cross_entropy_with_logits(
            feasibility_logits, target_feasible, reduction="none"
        )
    )
    return utility_bce + feasibility_loss_weight * feasibility_bce


def evaluate_model(
    model: CandidateMLP,
    dataset: FrozenPolicyDataset,
    split: str,
    *,
    feasibility_loss_weight: float = 0.25,
) -> dict[str, float | int]:
    batch = _tensors(dataset, split)
    with torch.no_grad():
        inputs, target_scores, target_feasible, weights = batch
        utility, feasibility_logits = model(inputs)
        feasibility_probability = torch.sigmoid(feasibility_logits)
        utility_mse = torch.sum(weights * torch.square(utility - target_scores)).item()
        utility_bce = torch.sum(
            weights * F.binary_cross_entropy(utility, target_scores, reduction="none")
        ).item()
        feasibility_bce = torch.sum(
            weights
            * F.binary_cross_entropy_with_logits(
                feasibility_logits, target_feasible, reduction="none"
            )
        ).item()
        feasibility_accuracy = torch.sum(
            weights * ((feasibility_probability >= 0.5) == (target_feasible >= 0.5))
        ).item()
        final_scores = (utility * feasibility_probability).cpu().numpy()
    offset = 0
    hits = 0
    for example in dataset.splits[split]:
        count = len(example.candidate_keys)
        predicted = final_scores[offset : offset + count].copy()
        predicted[~np.asarray(example.candidate_mask, dtype=bool)] = -1.0
        chosen = int(np.argmax(predicted))
        feasible_scores = [
            score
            for score, possible in zip(
                example.target_scores, example.target_feasible, strict=True
            )
            if possible
        ]
        best = max(feasible_scores)
        if example.target_feasible[chosen] and example.target_scores[chosen] == best:
            hits += 1
        offset += count
    return {
        "utility_mse": utility_mse,
        "utility_bce": utility_bce,
        "feasibility_bce": feasibility_bce,
        "feasibility_accuracy": feasibility_accuracy,
        "total_loss": utility_bce + feasibility_loss_weight * feasibility_bce,
        "optimal_set_hits": hits,
        "observation_count": len(dataset.splits[split]),
    }


def train_seed(
    dataset: FrozenPolicyDataset,
    *,
    seed: int,
    epochs: int = 2000,
    learning_rate: float = 0.01,
    weight_decay: float = 0.0,
    feasibility_loss_weight: float = 0.25,
) -> TrainingResult:
    if type(seed) is not int or seed < 0 or type(epochs) is not int or epochs < 1:
        raise ValueError("seed and epochs must be positive integers")
    _seed_everything(seed)
    model = CandidateMLP()
    optimizer = torch.optim.Adam(
        model.parameters(), lr=learning_rate, weight_decay=weight_decay
    )
    batch = _tensors(dataset, "train")
    for _ in range(epochs):
        optimizer.zero_grad(set_to_none=True)
        loss = _loss(model, batch, feasibility_loss_weight)
        if not torch.isfinite(loss):
            raise ValueError("Non-finite training loss")
        loss.backward()
        optimizer.step()
    state = {
        name: value.detach().cpu().clone()
        for name, value in model.state_dict().items()
    }
    metrics = {
        split: evaluate_model(
            model,
            dataset,
            split,
            feasibility_loss_weight=feasibility_loss_weight,
        )
        for split in ("train", "validation")
    }
    return TrainingResult(seed=seed, state_dict=state, metrics=metrics)


def export_state_dict(state_dict: dict[str, torch.Tensor]) -> dict[str, np.ndarray]:
    if set(state_dict) != set(WEIGHT_NAMES):
        raise ValueError("Unexpected model state dictionary")
    arrays = {
        WEIGHT_NAMES[name]: tensor.detach().cpu().numpy().astype(np.float32, copy=True)
        for name, tensor in state_dict.items()
    }
    if not all(np.isfinite(value).all() for value in arrays.values()):
        raise ValueError("Non-finite model parameter")
    return arrays


def write_deterministic_npz(path: Path, arrays: dict[str, np.ndarray]):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        for name in sorted(arrays):
            array = np.asarray(arrays[name])
            buffer = io.BytesIO()
            np.lib.format.write_array(buffer, array, allow_pickle=False)
            info = zipfile.ZipInfo(f"{name}.npy", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o600 << 16
            archive.writestr(info, buffer.getvalue())


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value):
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _model_from_state(state_dict: dict[str, torch.Tensor]) -> CandidateMLP:
    model = CandidateMLP()
    model.load_state_dict(state_dict, strict=True)
    model.eval()
    return model


def _idle_baseline(dataset: FrozenPolicyDataset, split: str):
    squared = 0.0
    hits = 0
    rows = dataset.splits[split]
    for example in rows:
        predicted = [1.0 if key == (None, "idle") else 0.0 for key in example.candidate_keys]
        squared += sum(
            (left - right) ** 2
            for left, right in zip(predicted, example.target_scores, strict=True)
        ) / len(predicted)
        chosen = predicted.index(max(predicted))
        best = max(
            score
            for score, possible in zip(
                example.target_scores, example.target_feasible, strict=True
            )
            if possible
        )
        hits += int(example.target_feasible[chosen] and example.target_scores[chosen] == best)
    return {"utility_mse": squared / len(rows), "optimal_set_hits": hits}


def _model_card(summary: dict[str, object], weights_sha: str, normalization_sha: str) -> str:
    selected = summary["selected_seed"]
    train = summary["seeds"][str(selected)]["metrics"]["train"]
    validation = summary["seeds"][str(selected)]["metrics"]["validation"]
    test = summary["selected_test_metrics"]
    return f"""# A-N3 Small-Sample Learned Scorer

Model version: `a-n3-mlp-v1`
Feature schema: `policy-features-v1`
Weights SHA256: `{weights_sha}`
Normalization SHA256: `{normalization_sha}`

## Intended use

Candidate scoring over public `Observation` inputs for B's guarded runner integration. The model returns every robust/fast candidate and one idle candidate. Missing RUL is supported because RUL is not a feature.

## Training

Frozen synthetic split: 12 train / 4 validation / 4 test. Selected seed: `{selected}` by minimum validation total loss, lower seed as tie-break. Train utility MSE: `{train['utility_mse']}`; train optimal-set hits: `{train['optimal_set_hits']}/12`. Validation total loss: `{validation['total_loss']}`. Test utility MSE (evaluated once after selection): `{test['utility_mse']}`.

## Failure and fallback

Missing/corrupt weights, hash or schema mismatch, invalid input and non-finite inference raise `LearnedPolicyError`. B's gateway owns timeout and explicit EDF fallback; Guard remains authoritative for physical feasibility.

## Limitations

Synthetic small-sample pipeline and overfit validation only. No generalization, policy-superiority, mature-optimizer, real-satellite or in-orbit claim.
"""


def run_training(config_path: Path, output: Path) -> dict[str, object]:
    config_path, output = Path(config_path), Path(output)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output must be new or empty")
    output.mkdir(parents=True, exist_ok=True)
    dataset = load_frozen_dataset(config_path)
    optimizer = config["optimizer"]
    if optimizer.get("utility_loss") != "binary_cross_entropy_soft_target":
        raise ValueError("Unexpected utility loss")
    results = [
        train_seed(
            dataset,
            seed=seed,
            epochs=optimizer["epochs"],
            learning_rate=optimizer["learning_rate"],
            weight_decay=optimizer["weight_decay"],
            feasibility_loss_weight=optimizer["feasibility_loss_weight"],
        )
        for seed in config["training_seeds"]
    ]
    selected = min(
        results,
        key=lambda result: (result.metrics["validation"]["total_loss"], result.seed),
    )
    model = _model_from_state(selected.state_dict)
    test_metrics = evaluate_model(
        model,
        dataset,
        "test",
        feasibility_loss_weight=optimizer["feasibility_loss_weight"],
    )
    train_metrics = selected.metrics["train"]
    gate = config["overfit_gate"]
    passed = (
        train_metrics["utility_mse"] <= gate["max_train_utility_mse"]
        and train_metrics["optimal_set_hits"] == gate["required_train_optimal_set_hits"]
    )
    if not passed:
        raise ValueError(f"Overfit gate failed: {train_metrics}")
    weights_path = output / "weights.npz"
    write_deterministic_npz(weights_path, export_state_dict(selected.state_dict))
    normalization_path = output / "normalization.json"
    _write_json(normalization_path, dataset.normalization.as_dict())
    try:
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        revision = "unversioned"
    summary = {
        "schema_version": "policy-training-summary-v1",
        "model_version": "a-n3-mlp-v1",
        "feature_schema_version": "policy-features-v1",
        "source_revision": revision,
        "samples_sha256": dataset.samples_sha256,
        "split_sha256": dataset.split_sha256,
        "training_seeds": config["training_seeds"],
        "selection_rule": "minimum validation total_loss; lower seed tie-break",
        "selected_seed": selected.seed,
        "seeds": {
            str(result.seed): {"metrics": result.metrics} for result in results
        },
        "selected_test_metrics": test_metrics,
        "test_evaluated_after_selection": True,
        "overfit_gate": {**gate, "passed": passed},
        "idle_baseline": {
            split: _idle_baseline(dataset, split)
            for split in ("train", "validation", "test")
        },
        "limitations": (
            "synthetic small-sample validation; no generalization or policy-superiority claim"
        ),
    }
    summary_path = output / "training_summary.json"
    _write_json(summary_path, summary)
    weights_sha = _sha256(weights_path)
    normalization_sha = _sha256(normalization_path)
    model_card_path = output / "model_card.md"
    model_card_path.write_text(
        _model_card(summary, weights_sha, normalization_sha),
        encoding="utf-8",
        newline="\n",
    )
    manifest = {
        "schema_version": "policy-model-manifest-v1",
        "model_version": "a-n3-mlp-v1",
        "feature_schema_version": "policy-features-v1",
        "source_revision": revision,
        "selected_seed": selected.seed,
        "array_names": sorted(export_state_dict(selected.state_dict)),
        "artifacts_sha256": {
            path.name: _sha256(path)
            for path in (
                weights_path,
                normalization_path,
                summary_path,
                model_card_path,
            )
        },
        "config_sha256": _sha256(config_path),
        "limitations": summary["limitations"],
    }
    _write_json(output / "manifest.json", manifest)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/policy_train.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = run_training(args.config, args.output)
    print(
        json.dumps(
            {
                "selected_seed": summary["selected_seed"],
                "overfit_gate": summary["overfit_gate"],
                "seeds": summary["seeds"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
