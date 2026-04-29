from pathlib import Path

from app.ingest.sources import discover_shards, iter_resources

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "tiny"


def test_discover_shards_groups_paths_by_resource_type():
    shards = discover_shards(FIXTURE_DIR)

    assert set(shards.keys()) == {"Patient", "Condition", "Observation"}
    assert shards["Patient"][0].name == "Patient.000.ndjson"


def test_iter_resources_yields_parsed_dicts():
    shards = discover_shards(FIXTURE_DIR)

    patients = list(iter_resources(shards["Patient"]))

    assert len(patients) == 2
    assert patients[0]["resourceType"] == "Patient"
    assert patients[0]["id"] == "p1"


def test_iter_resources_skips_blank_lines(tmp_path: Path):
    shard = tmp_path / "X.000.ndjson"
    shard.write_text(
        '{"resourceType":"X","id":"1"}\n\n{"resourceType":"X","id":"2"}\n'
    )

    out = list(iter_resources([shard]))

    assert [r["id"] for r in out] == ["1", "2"]
