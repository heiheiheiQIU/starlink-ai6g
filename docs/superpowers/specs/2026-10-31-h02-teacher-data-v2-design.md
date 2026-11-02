# H02 Teacher Data v2 Design

## Objective

Replace the rejected H02 teacher-data candidate with a new, independently
auditable v2 delivery containing 20 genuinely distinct public Observations and
a leakage-safe 12/4/4 train/validation/test split. The old
`data/teacher/a_n3_20/` delivery and the historical B evidence remain unchanged.

This design addresses only the A-N3 teacher-data stage. It does not claim that
the learned policy, model training, or AI effectiveness evidence is complete.

## Fixed constraints

- Branch baseline remains `origin/feature/ai@866df43d124e62a77081a7acd2e095c98b34c172`.
- Work continues on `codex/a-next`; the branch is retained until B accepts the
  replacement delivery.
- Do not modify the public `Observation`, `CandidateScore`, `TeacherResult`,
  `solve_teacher`, or Guard contracts.
- Do not edit or replace `docs/evidence/B/H02_2026-10-29/` or
  `data/teacher/a_n3_20/`; both are historical evidence.
- All new data is synthetic and must be described as synthetic.
- The 20-row set is for interface and pipeline validation, not for training or
  performance claims.

## Selected approach

Create a parallel v2 source and delivery:

- Source: `data/teacher/sources/a_n3_20_v2.jsonl`
- Frozen outputs: `data/teacher/a_n3_20_v2/`
- A-to-B handoff: `docs/handoffs/A_N3_data_v2_A_2026-10-31.md`

Each source row contains `sample_id`, `source_group_id`, and one public
`observation`. The 20 rows use 20 different source groups and 20 different
decision inputs. They stay inside the existing teacher's supported domain and
vary public task, window, link-rate, priority, and health-estimate fields.

The existing generator recomputes every label through `solve_teacher` and
`validate_teacher_result`; no old labels are copied into v2.

## Observation content identity

The generator derives `observation_content_sha256` from canonical JSON after
removing only top-level `run_id` and `policy_id`. No task, forecast, health,
time, inflight, or cache field is removed. Therefore changing a display or
execution identifier cannot make identical decision inputs appear independent.

Before any teacher call or output publication, dataset validation enforces:

1. `sample_id` is non-empty and unique.
2. `source_group_id` is non-empty and traceable.
3. `run_id` remains unique for this 20-row H02 delivery.
4. `observation_content_sha256` is unique across all 20 rows.
5. Hidden-truth fields remain forbidden.

An exact duplicate fails with a controlled `DUPLICATE_OBSERVATION_CONTENT`
error even when its `run_id`, `policy_id`, sample ID, or source group differs.
This validation happens before solving, staging, or publication.

Every output record preserves `source_group_id` and
`observation_content_sha256`. Both fields enter the stable label-content hash,
so provenance changes invalidate the frozen label hash.

## Split behavior

`training/splits.py` changes from scenario-only partitioning to source-group
partitioning for v2. The deterministic ordering key is SHA-256 over the split
seed and `source_group_id`; the algorithm version becomes
`source-group-sha256-v2`.

The v2 manifest records, for each split:

- source group IDs;
- scenario IDs;
- sample IDs;
- observation-content hashes;
- counts for each field.

It records pairwise intersections for all four identities. All intersections
must be empty, and the union of each identity must cover the complete source.
The splitter independently recomputes each content hash from the embedded
Observation and rejects a mismatched stored hash or duplicate content.

For H02 v2, each source group contains exactly one scenario and one sample, so
the deterministic split remains 12 train, 4 validation, and 4 test rows. The
group-first representation is retained for later multi-state trajectory data,
where several distinct observations may share one source group and must stay in
one split.

## Configuration and compatibility

`configs/policy_train.json` points to the v2 frozen outputs, records the v2
split algorithm, and remains `training_enabled: false`. No model is trained as
part of this correction.

The old v1 files remain readable historical artifacts. New validation is
exercised against v2 input and generated records; the code does not rewrite old
hashes or claim that the rejected v1 split is accepted.

## Error handling and publication

All structural, provenance, duplicate-content, and path checks complete before
the first teacher invocation. A failed preflight publishes no output directory.
Per-sample solver failures keep the existing evidence-preserving behavior: the
dataset is published as `blocked`, and the failed sample is retained without
private exception text.

The v2 output directory is generated through the existing staging-and-rename
flow and cannot overwrite an existing non-empty destination. Frozen files use
canonical JSON and LF line endings.

## Verification

Tests are added before production changes and must demonstrate the original
failure mode:

- two observations differing only in `run_id`/`policy_id` are rejected before
  solving;
- a forged or mismatched content hash is rejected by the splitter;
- two distinct states from one source group stay in one split;
- all v2 split identity intersections are empty and all identities are fully
  covered;
- the 20 frozen source observations have 20 unique content hashes;
- regenerated labels and all output SHA-256 values match the committed v2
  artifacts;
- feature extraction reads public Observation fields only;
- existing teacher-data, feature, split, and H02 tests do not regress.

The final handoff lists the exact candidate commit, source/output hashes,
generation commands, targeted-test result, synthetic-data limitation, and the
request for B to recompute labels and recheck the split independently.

## Out of scope

- A-N2 health-data split manifest.
- Large-scale B-generated training data.
- `backend/policies/learned.py` and model weights.
- Training curves, learned-policy metrics, or competition claims.
- Changes to B or C implementation branches.
