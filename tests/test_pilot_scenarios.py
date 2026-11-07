from training.pilot_scenarios import build_sources, build_source_splits

def test_sources_are_deterministic_unique_and_cover_declared_families():
    first = build_sources()
    second = build_sources()
    assert first == second
    assert len(first) == 30
    assert len({row["source_id"] for row in first}) == 30
    assert len({row["seed"] for row in first}) == 30
    assert not ({row["seed"] for row in first} & set(range(200000, 200180)))
    assert len({row["content_sha256"] for row in first}) == 30
    families = [row["family"] for row in first]
    assert families.count("decision") == 24
    assert families.count("low_energy") == 2
    assert families.count("no_window") == 2
    assert families.count("deadline_before_window") == 2

def test_source_split_is_source_first_complete_and_disjoint():
    sources = build_sources()
    manifest = build_source_splits(
        sources, split_seed=20261104, counts=(18, 6, 6)
    )
    assert manifest["counts"] == {"train": 18, "validation": 6, "test": 6}
    groups = [set(manifest["splits"][name]) for name in ("train", "validation", "test")]
    assert all(not groups[i] & groups[j] for i in range(3) for j in range(i + 1, 3))
    assert set.union(*groups) == {row["source_id"] for row in sources}


def test_pilot_configuration_is_exact_and_training_disabled():
    import json
    from pathlib import Path

    expected = json.loads("{\"schema_version\":\"policy-pilot-config-v1\",\"dataset_version\":\"a-n4-pilot-v1\",\"output_path\":\"data/teacher/a_n4_pilot_v1\",\"source_count\":30,\"split_seed\":20261104,\"split_counts\":{\"train\":18,\"validation\":6,\"test\":6},\"states_per_source_min\":2,\"states_per_source_max\":4,\"valid_state_min\":60,\"valid_state_max\":120,\"teacher_config_path\":\"configs/teacher.json\",\"teacher_version\":\"bounded-forecast-r4-v1\",\"teacher_budget_ms\":1000,\"cpu_budget_s\":7200,\"limited_result_stop_count\":3,\"training_enabled\":false}")
    actual = json.loads(
        (Path(__file__).resolve().parents[1] / "configs/policy_pilot.json")
        .read_text(encoding="utf-8")
    )
    assert actual == expected
    assert actual["training_enabled"] is False


def test_protocol_writes_canonical_files_and_refuses_overwrite(tmp_path):
    import json
    import pytest
    from training.pilot_scenarios import canonical_json, write_source_protocol

    paths = write_source_protocol(tmp_path / "protocol")
    rows = [json.loads(line) for line in paths["sources"].read_text(encoding="utf-8").splitlines()]
    assert rows == build_sources()
    manifest = json.loads(paths["splits"].read_text(encoding="utf-8"))
    assert manifest == build_source_splits(rows, split_seed=20261104, counts=(18, 6, 6))
    assert paths["sources"].read_bytes() == "".join(canonical_json(row) + "\n" for row in rows).encode("utf-8")
    with pytest.raises(ValueError, match="must be empty"):
        write_source_protocol(tmp_path / "protocol")


def test_split_is_input_order_independent_and_rejects_invalid_membership():
    import pytest

    rows = build_sources()
    assert build_source_splits(rows, split_seed=20261104, counts=(18, 6, 6)) == build_source_splits(
        list(reversed(rows)), split_seed=20261104, counts=(18, 6, 6)
    )
    with pytest.raises(ValueError, match="do not match"):
        build_source_splits(rows[:-1], split_seed=20261104, counts=(18, 6, 6))
    with pytest.raises(ValueError, match="do not match"):
        build_source_splits(rows[:-1] + [rows[0]], split_seed=20261104, counts=(18, 6, 6))
