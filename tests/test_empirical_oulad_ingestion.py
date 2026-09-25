import json
from pathlib import Path

import pytest

from scripts.ingest_oulad_empirical import validate_prepared


def test_manifest_validation_accepts_verified_empirical_fixture(tmp_path: Path):
    source = Path(r"G:\Queen's\Graduation Project\Digital-Twin-runtime\data\processed\oulad_runtime_AAA_2013J_v3")
    target = tmp_path / "prepared"
    target.mkdir()
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    (target / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    for name in manifest["outputs"]:
        (target / name).write_bytes((source / name).read_bytes())
    result = validate_prepared(target)
    assert result["presentation_id"] == "oulad:AAA:2013J"
    assert result["data_origin"] == "empirical"


def test_manifest_validation_rejects_replay_or_mismatch(tmp_path: Path):
    (tmp_path / "manifest.json").write_text(json.dumps({"module": "AAA", "presentation": "2013J", "presentation_id": "moodle-replay:AAA:2030A", "data_origin": "replayed", "outputs": {}}))
    with pytest.raises(ValueError, match="invalid presentation or origin"):
        validate_prepared(tmp_path)


def test_manifest_validation_rejects_missing_artifact(tmp_path: Path):
    (tmp_path / "manifest.json").write_text(json.dumps({"module": "AAA", "presentation": "2013J", "presentation_id": "oulad:AAA:2013J", "data_origin": "empirical", "outputs": {}}))
    with pytest.raises(ValueError, match="missing prepared artifact"):
        validate_prepared(tmp_path)
