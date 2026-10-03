import csv
from pathlib import Path

from scripts.evaluate_predictive_baselines import bootstrap

ART = Path(r"G:\Queen's\Graduation Project\Digital-Twin-evaluation-artifacts\oulad_AAA_2013J_v1")


def test_empirical_artifact_has_frozen_split_and_expected_checkpoints():
    states = list(csv.DictReader((ART / "states.csv").open(encoding="utf-8")))
    splits = list(csv.DictReader((ART / "split_manifest.csv").open(encoding="utf-8")))
    assert len(states) == 1464
    assert {int(r["checkpoint"]) for r in states} == {3, 5, 8, 10}
    assert {r["partition"] for r in splits} == {"train", "validation", "test"}
    assert len({r["learner_id"] for r in splits}) == len(splits)


def test_empirical_artifact_temporal_provenance_has_no_cutoff_violation():
    rows = csv.DictReader((ART / "temporal_provenance.csv").open(encoding="utf-8"))
    assert all(int(r["source_time"]) <= int(r["checkpoint_time"]) for r in rows)


def test_bootstrap_returns_bounded_ci_for_auc():
    low, high = bootstrap([0, 1, 0, 1], [0.1, 0.9, 0.2, 0.8], 0.5, "auroc", n=100)
    assert 0.0 <= low <= high <= 1.0
