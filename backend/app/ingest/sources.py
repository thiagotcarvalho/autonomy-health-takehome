"""Discovery and streaming parse of FHIR bulk NDJSON shards."""

from collections import defaultdict
from collections.abc import Iterable, Iterator
from pathlib import Path

import orjson


def discover_shards(data_dir: Path) -> dict[str, list[Path]]:
    """Groups NDJSON shards in a directory by FHIR resource type.

    The resource type is derived from the filename prefix preceding the
    first dot, i.e. `Patient.000.ndjson` is grouped under `"Patient"`.
    Files within a type are returned sorted by name so iteration order is
    deterministic across runs.

    Args:
        data_dir: Directory containing FHIR bulk `*.ndjson` shards.

    Returns:
        A mapping from resource type to a list of shard paths.
    """
    shards: dict[str, list[Path]] = defaultdict(list)
    for path in sorted(data_dir.glob("*.ndjson")):
        resource_type = path.name.split(".", 1)[0]
        shards[resource_type].append(path)
    return dict(shards)


def iter_resources(shards: Iterable[Path]) -> Iterator[dict]:
    """Streams parsed FHIR resources from a sequence of NDJSON shards.

    Reads each shard line by line so memory stays flat regardless of the
    dataset size. Blank lines are skipped silently. Malformed JSON raises
    `orjson.JSONDecodeError` from the underlying parser.

    Args:
        shards: Iterable of shard paths to read in order.

    Yields:
        One parsed FHIR resource dict per non-blank line.
    """
    for shard in shards:
        with shard.open("r", encoding="utf-8") as shard_file:
            for line in shard_file:
                line = line.strip()
                if not line:
                    continue
                yield orjson.loads(line)
