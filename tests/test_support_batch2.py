from datetime import timezone

import pytest
from pydantic import TypeAdapter

from digital_twin.api.support_schemas import CreateCase, SupportActionRequest
from digital_twin.persistence.support import ACTIVE, TRANSITIONS


def test_support_contract_and_lifecycle_constants():
    request = CreateCase(learner_id="l1", idempotency_key="create-1")
    assert request.learner_id == "l1"
    assert set(ACTIVE) == {"new_concern", "reviewed", "ongoing"}
    assert "resolved" in TRANSITIONS["new_concern"]
    assert "dismissed" in TRANSITIONS["ongoing"]


def test_follow_up_normalizes_to_utc():
    adapter = TypeAdapter(SupportActionRequest)
    request = adapter.validate_python({
        "action_type": "set_follow_up",
        "follow_up_due_at": "2026-09-24T12:00:00+02:00",
        "expected_version": 1,
        "idempotency_key": "follow-up-1",
    })
    assert request.follow_up_due_at.tzinfo == timezone.utc
    assert request.follow_up_due_at.hour == 10


def test_action_keys_are_required():
    adapter = TypeAdapter(SupportActionRequest)
    with pytest.raises(ValueError):
        adapter.validate_python({"action_type": "add_note", "expected_version": 1})
