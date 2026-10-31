# A-N3 Learned Scorer Design

Date: 2026-10-31
Owner: A
Status: proposed for review; no training or learned runtime has been implemented by this document

## 1. Objective and frozen inputs

Build A's first auditable learned candidate scorer on the accepted H02 v2 synthetic teacher dataset, then hand B a stable `score_actions(observation, *, config=None)` implementation, frozen weights, hashes, normalization, model card, latency evidence and failure examples.

The design binds to:

- A data branch `codex/a-next@2cfe89cfa2e990c4d488861c0fd4a57ae2e3ac67`;
- accepted v2 data candidate `8f206b4f6d029ddaf3cfd6163777e0c9a57b03ee`;
- source revision `38a1a7463bfe0c8eaecf1bb729b98aa74ae0040b`;
- `data/teacher/a_n3_20_v2/samples.jsonl` and its frozen `12/4/4` source-group split;
- feature schema `policy-features-v1`, with 14 global and 9 candidate features;
- B's draft learned integration contract in `origin/feature/shared-channel-r5@181dacc`.

This work is a small-sample pipeline and overfit check. It is not a generalization claim, a mature optimizer, a real-satellite result, an R5 learned-policy experiment, or the formal 18×10 AI experiment.

## 2. Approaches considered

### A. PyTorch model with a `.pt` runtime artifact

This is the shortest implementation path, but the runtime artifact is pickle-based, harder to audit safely, and couples inference to PyTorch loading behavior. It is not selected.

### B. Linear score regression

This is highly auditable and useful as a sanity baseline, but it is unlikely to represent interactions among energy bounds, window state, deadline and action mode. It will be retained as a reported baseline, not the delivered learned scorer.

### C. Shared candidate MLP trained in PyTorch, exported to non-pickle NumPy weights

This is selected. Training uses PyTorch for deterministic optimization. Runtime inference uses validated NumPy arrays loaded with `allow_pickle=False`. The model is small enough to inspect and fast enough for B's initial 100 ms gateway budget.

## 3. Input, action order and mask

`training.policy_features.encode_observation()` remains the only feature encoder. No truth-only simulator fields or RUL surrogate values are introduced.

Each candidate input is the concatenation of:

1. 14 global features, in the exact order already frozen in `configs/policy_train.json`;
2. 9 candidate features, in the exact frozen order.

The resulting width is 23. Raw units remain seconds, bytes, Wh, bit/s, probabilities, counts and one-hot indicators as named by the schema. Missing RUL requires no imputation because RUL is not a model feature.

Candidate keys and order are frozen as:

1. tasks sorted by `task_id`;
2. `robust`, then `fast` for each task;
3. exactly one `(None, "idle")` candidate last.

The existing structural mask is retained:

- a send candidate is structurally available only when there is no inflight block, the task is not expired and remaining bytes are positive;
- idle is always structurally available;
- the scorer still returns the complete candidate key set required by B;
- structurally masked send candidates receive the finite score `-1.0`, lower than the model's `[0, 1]` output range;
- B's Guard remains authoritative for link, deadline, power, energy, reserve and protocol feasibility. Learned inference cannot bypass Guard or the retry lock.

## 4. Label alignment and model

Every eligible sample must satisfy all of the following before training:

- solver status is `OPTIMAL`, gap is `0.0` and `label_eligible` is true;
- dataset, manifest and split hashes match the frozen files;
- sample, scenario, source-group and observation hashes match the split manifest;
- teacher candidate keys form the same unique set as the encoder candidate keys; labels are joined by `(task_id, mode)` and reordered to the frozen encoder order rather than trusting JSON list order;
- all teacher scores are finite and all teacher feasibility values are booleans.

The frozen 20 labels contain ties: some observations have 2, 3 or 5 teacher-optimal candidates. Therefore the trainer must not collapse each observation to an arbitrary single class.

The selected model is shared across a variable number of candidates:

```text
23 inputs -> Linear(32) -> ReLU -> Linear(16) -> ReLU
          -> utility head: Linear(1) -> sigmoid
          -> feasibility head: Linear(1) logits
```

For each candidate:

- utility target is the teacher score;
- feasibility target is the teacher `feasible` flag;
- training loss is `BCE(utility, soft_teacher_score) + 0.25 * BCEWithLogits(feasibility, feasible)`; utility MSE remains the reported overfit metric and gate;
- inference score is `utility * sigmoid(feasibility)` for unmasked candidates;
- ties remain valid because training regresses the full score vector rather than inventing a single chosen action.

The auxiliary feasibility head helps the tiny dataset express teacher support, but it is not a replacement for Guard. A model prediction cannot itself certify physical feasibility.

## 5. Normalization and leakage control

Normalization statistics are fitted from the 12 frozen train observations only:

- global mean and standard deviation are computed once per observation, so an observation with two tasks is not overweighted by repeated global rows;
- candidate mean and standard deviation are computed over train candidate rows;
- zero or non-finite standard deviations are rejected or replaced by the documented scale `1.0` only for a truly constant finite feature;
- validation and test rows only consume the frozen train statistics;
- test data is never used for normalization, hyperparameters, checkpoint selection, seed selection or stopping.

The normalization JSON records feature names, order, units, means, scales, source split, source file SHA256 and schema version. Runtime refuses a feature-name or version mismatch.

## 6. Training protocol and model selection

Training is CPU-only and deterministic. The frozen seeds are `20261031`, `20261032` and `20261033`. Each run sets Python, NumPy and PyTorch seeds and enables deterministic algorithms.

Initial frozen hyperparameters:

- optimizer: Adam;
- learning rate: `0.01`;
- weight decay: `0.0`;
- epochs: `2000`;
- full train split per optimization step;
- float32 parameters and inference arrays.

For each seed, retain final train and validation metrics. Select one seed by lowest validation total loss, with the numerically smaller seed as the deterministic tie-break. The test split is evaluated once after the seed and weights are frozen.

The small-sample learning check is:

- train utility MSE no greater than `1e-3`;
- predicted highest-score candidate belongs to the teacher's maximum-score feasible set for all 12 train observations;
- no non-finite loss, parameter, normalized feature or score.

Failure of this check stops delivery and triggers a design review; it must not be hidden by changing the split or using validation/test examples for training. Validation and test metrics are descriptive only and carry no generalization claim.

Approved correction on 2026-10-31: the initial sigmoid-plus-MSE objective saturated the only `2/3` soft utility label at `1.0`, producing a reproducible MSE floor of approximately `0.00185185` for all three seeds. A single-variable diagnostic using soft-target BCE reduced train utility MSE to approximately `1.06e-5` without changing data, architecture, seeds, epochs or evaluation gates. The utility training objective is therefore BCE; utility MSE remains the acceptance metric.

Report an idle-only and a linear baseline on the same frozen splits. These baselines are diagnostics, not additional policy claims.

## 7. Runtime interface and error behavior

Add `backend/policies/learned.py` with:

```python
def score_actions(observation, *, config=None) -> list[CandidateScore]:
    ...
```

The module:

1. validates the public `Observation`;
2. loads a server-controlled model package and verifies its SHA256, format, schema, array names, shapes, dtypes and finite values;
3. encodes and normalizes candidates in frozen order;
4. performs NumPy forward inference;
5. applies the structural mask score;
6. returns one finite `CandidateScore` per key, including one idle candidate.

It raises a controlled `LearnedPolicyError` for missing or corrupt artifacts, hash/version mismatch, invalid input, non-finite inference or malformed output. It does not silently substitute weights or call EDF itself. B's ScorerGateway/process supervisor owns timeout and EDF fallback, so fallback is visible in decision events rather than disguised as learned success.

The default package path comes from a repository-controlled config. Client requests never supply arbitrary local paths. Model loading is cached only after complete validation; tests can clear the cache. Loading time and pure forward time are recorded separately.

B's initial decision budget remains 100 ms. A will measure cold load and at least 1,000 warm scoring calls on CPU, reporting median, p95 and maximum. These measurements inform the final shared budget but do not change B's process-isolation design.

## 8. Artifacts and provenance

The proposed frozen package is:

```text
artifacts/models/a_n3_policy_v1/
  weights.npz
  normalization.json
  training_summary.json
  model_card.md
  manifest.json
```

`weights.npz` contains only named numeric arrays and is loaded with `allow_pickle=False`. `manifest.json` records:

- model and feature versions;
- selected seed and all three seed metrics;
- data, split, config, normalization and weight SHA256 values;
- exact source revision and training command;
- array names, shapes and dtypes;
- cold-load and warm-inference timings;
- stated synthetic/small-sample limitations.

The model card includes success, missing-RUL, invalid-input, missing/corrupt-weight and gateway-fallback examples. Raw run logs stay under ignored `runs/`; concise evidence and hashes go under `docs/evidence/A/`.

## 9. Code and test layout

Planned implementation files:

- `training/policy_dataset.py`: frozen-data verification, candidate/label alignment and train-only normalization;
- `training/train_policy.py`: deterministic three-seed training, baselines, export and manifest generation;
- `backend/policies/learned.py`: validated NumPy inference;
- `configs/learned_policy.json`: server-controlled artifact path, expected hashes and versions;
- `tests/test_policy_dataset.py` and `tests/test_learned_policy.py`;
- targeted additions for deterministic training/export behavior.

Required tests cover:

- wrong data/hash/split/version, cross-split leakage and ineligible labels;
- candidate order, variable task counts, unique idle, structural masks and teacher-key mismatch;
- train-only normalization and constant features;
- deterministic repeated export and non-pickle load;
- successful inference, missing RUL, invalid observation, corrupt/missing weights, hash mismatch, wrong shapes/dtypes, NaN/Inf and complete finite candidate output;
- ScorerGateway exception/timeout fallback without claiming learned success;
- existing EDF/value, H00 contracts, frozen schema and full repository regression.

No public contract or schema change is required for A's scorer. Any later B/C API or TypeScript change remains a separate three-party interface decision.

## 10. Delivery gates

Implementation is ready for B review only when:

1. all data and split gates pass without modifying frozen v2 artifacts;
2. three seeds and both diagnostic baselines are actually run;
3. the train overfit check passes as written;
4. selected weights, normalization, model card and all SHA256 values are frozen;
5. targeted and full tests pass;
6. warm and cold latency evidence is recorded;
7. `training_enabled` is changed only as part of the final verified artifact commit;
8. the handoff explicitly says synthetic small-sample validation and does not claim generalization or AI superiority.

After A hands off the scorer, B owns Runner/Guard/API/process integration and the later paired learned experiments. C owns UI consumption and visual/error-state acceptance.
