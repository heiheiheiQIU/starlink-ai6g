# A-N3 Small-Sample Learned Scorer

Model version: `a-n3-mlp-v1`
Feature schema: `policy-features-v1`
Weights SHA256: `a5226264d3a60f7d858e4d410595668b44b8dbd4c9a8bfa05191c1fd80461e4a`
Normalization SHA256: `5c5fd7e843817a63ed6c486ed1c2a525243a724a6573b01681e0aa53811d2449`

## Intended use

Candidate scoring over public `Observation` inputs for B's guarded runner integration. The model returns every robust/fast candidate and one idle candidate. Missing RUL is supported because RUL is not a feature.

## Training

Frozen synthetic split: 12 train / 4 validation / 4 test. Selected seed: `20261033` by minimum validation total loss, lower seed as tie-break. Train utility MSE: `5.849076778474682e-11`; train optimal-set hits: `12/12`. Validation total loss: `5.407445311546326`. Test utility MSE (evaluated once after selection): `0.356253057718277`.

## Runtime evidence

Frozen on Python 3.12.9 with NumPy 2.1.3, PyTorch 2.5.1 and Pydantic 2.12.3. Cold model load plus first score took `2.6265 ms`. Across 1,000 warm calls over the 20 frozen observations, median latency was `0.52445 ms`, p95 was `0.68487 ms` and maximum was `1.15960 ms`; all calls returned the complete finite candidate set. Loading and warm-forward time are reported separately.

## Failure and fallback

Missing/corrupt weights, hash or schema mismatch, invalid input and non-finite inference raise `LearnedPolicyError`. B's gateway owns timeout and explicit EDF fallback; Guard remains authoritative for physical feasibility.

## Limitations

Synthetic small-sample pipeline and overfit validation only. No generalization, policy-superiority, mature-optimizer, real-satellite or in-orbit claim.
