"""Read-only Moodle boundary and controlled OULAD replay adapter."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

import httpx
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError, model_validator

from digital_twin.persistence.store import stable_hash
from digital_twin.schemas import CanonicalObservation

MOODLE_ADAPTER_VERSION = "moodle-controlled-export-v1"
READ_ONLY_FUNCTIONS = frozenset(
    {
        "core_course_get_courses",
        "core_course_get_contents",
        "core_enrol_get_enrolled_users",
        "core_completion_get_activities_completion_status",
        "gradereport_user_get_grade_items",
    }
)


class ExportContract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ControlledExportHeader(ExportContract):
    schema_version: Literal["moodle-controlled-export-v1"] = "moodle-controlled-export-v1"
    source_id: str = Field(min_length=1, max_length=128)
    source_name: str = Field(min_length=1, max_length=200)
    presentation_id: str = Field(min_length=1, max_length=128)
    module_code: str = Field(min_length=1, max_length=64)
    presentation_code: str = Field(min_length=1, max_length=64)
    length_days: int = Field(ge=1, le=730)
    course_start_at: AwareDatetime
    exported_at: AwareDatetime
    data_origin: Literal["replayed"] = "replayed"
    scenario_id: str = Field(min_length=1, max_length=128)
    warning: str = Field(min_length=1, max_length=500)


class MoodleExportRecord(ExportContract):
    record_type: Literal["enrolment", "event", "grade"]
    source_record_id: str = Field(min_length=1, max_length=128)
    source_user_id: str = Field(min_length=1, max_length=128)
    event_code: str = Field(min_length=1, max_length=128)
    occurred_at: AwareDatetime
    available_at: AwareDatetime | None = None
    time_precision: Literal["exact", "day"]
    value: float | int | bool | str | None = None
    count: int | None = Field(default=None, ge=0)
    metadata: dict[str, str | int | float | bool | None] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_payload(self):
        if self.value is None and self.count is None:
            raise ValueError("a Moodle export record requires value or count")
        if self.available_at is not None and self.available_at < self.occurred_at:
            raise ValueError("available_at cannot precede occurred_at")
        return self


class ControlledExport(ExportContract):
    header: ControlledExportHeader
    records: list[dict[str, Any]]

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def read(cls, path: Path) -> ControlledExport:
        return cls.model_validate_json(path.read_text(encoding="utf-8"))


class ReplayWatermark(ExportContract):
    occurred_at: AwareDatetime | None = None
    source_record_id: str | None = Field(default=None, max_length=128)

    def as_tuple(self) -> tuple[str, str]:
        return (
            self.occurred_at.astimezone(UTC).isoformat() if self.occurred_at else "",
            self.source_record_id or "",
        )


@dataclass(frozen=True)
class QuarantineCandidate:
    source_record_id: str
    reason_code: str
    payload_hash: str
    errors: list[dict[str, Any]]


@dataclass(frozen=True)
class MappingBatch:
    observations: list[CanonicalObservation]
    quarantines: list[QuarantineCandidate]
    watermark: ReplayWatermark
    scanned_count: int


class MoodleControlledExportAdapter:
    def __init__(self, header: ControlledExportHeader):
        self.header = header

    def map_records(
        self,
        records: list[dict[str, Any]],
        *,
        run_id: str,
        after: ReplayWatermark,
        through_at: datetime,
        recover_source_ids: set[str] | None = None,
    ) -> MappingBatch:
        recover_source_ids = recover_source_ids or set()
        observations: list[CanonicalObservation] = []
        quarantines: list[QuarantineCandidate] = []
        cursor = after
        scanned = 0
        for raw in records:
            source_record_id = _safe_source_record_id(raw)
            raw_cursor = _raw_cursor(raw, source_record_id)
            if raw_cursor is None:
                if after.occurred_at is not None:
                    continue
                scanned += 1
                try:
                    MoodleExportRecord.model_validate(raw)
                except ValidationError as error:
                    quarantines.append(
                        QuarantineCandidate(
                            source_record_id=source_record_id,
                            reason_code="SCHEMA_VALIDATION_FAILED",
                            payload_hash=stable_hash(raw),
                            errors=_safe_validation_errors(error),
                        )
                    )
                continue
            if raw_cursor[0] > through_at.astimezone(UTC):
                continue
            if source_record_id not in recover_source_ids and raw_cursor <= _watermark_tuple(after):
                continue
            scanned += 1
            if raw_cursor > _watermark_tuple(cursor):
                cursor = ReplayWatermark(
                    occurred_at=raw_cursor[0], source_record_id=raw_cursor[1]
                )
            try:
                record = MoodleExportRecord.model_validate(raw)
                observation = self._map_record(record, run_id)
            except ValidationError as error:
                quarantines.append(
                    QuarantineCandidate(
                        source_record_id=source_record_id,
                        reason_code="SCHEMA_VALIDATION_FAILED",
                        payload_hash=stable_hash(raw),
                        errors=_safe_validation_errors(error),
                    )
                )
                continue
            observations.append(observation)
        return MappingBatch(observations, quarantines, cursor, scanned)

    def _map_record(self, record: MoodleExportRecord, run_id: str) -> CanonicalObservation:
        occurred_at = record.occurred_at.astimezone(UTC)
        available_at = (record.available_at or record.occurred_at).astimezone(UTC)
        course_day = (occurred_at.date() - self.header.course_start_at.date()).days
        available_course_day = (
            available_at.date() - self.header.course_start_at.date()
        ).days
        kind = {"enrolment": "enrolment", "event": "activity", "grade": "assessment"}[
            record.record_type
        ]
        learner_id = _learner_id(self.header.scenario_id, record.source_user_id)
        identity = stable_hash(
            {
                "source_id": self.header.source_id,
                "source_record_id": record.source_record_id,
                "record_type": record.record_type,
            }
        )
        return CanonicalObservation(
            observation_id=f"moodle-replay:obs:{identity[:24]}",
            source_id=self.header.source_id,
            ingestion_run_id=run_id,
            learner_id=learner_id,
            presentation_id=self.header.presentation_id,
            kind=kind,
            event_code=record.event_code,
            event_at=occurred_at,
            course_day=course_day,
            available_at=available_at,
            available_course_day=available_course_day,
            time_precision=record.time_precision,
            value=record.value,
            count=record.count,
            source_record_id=record.source_record_id,
            data_origin="replayed",
            adapter_version=MOODLE_ADAPTER_VERSION,
            metadata={"record_type": record.record_type, **record.metadata},
        )


class MoodleWebServiceReader:
    """Minimal Moodle REST reader that refuses non-allow-listed functions."""

    def __init__(
        self,
        *,
        base_url: str,
        token: str,
        timeout_seconds: float = 15.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        url = httpx.URL(base_url)
        if url.scheme not in {"http", "https"} or not url.host:
            raise ValueError("Moodle URL must be an absolute HTTP(S) URL")
        if url.scheme == "http" and url.host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("unencrypted Moodle access is allowed only on loopback")
        if not token:
            raise ValueError("Moodle web-service token is required")
        self.endpoint = str(url).rstrip("/") + "/webservice/rest/server.php"
        self.token = token
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    def call(self, function: str, **parameters: Any) -> Any:
        if function not in READ_ONLY_FUNCTIONS:
            raise ValueError(f"Moodle function is not approved for read-only use: {function}")
        payload = {
            "wstoken": self.token,
            "moodlewsrestformat": "json",
            "wsfunction": function,
            **_flatten_moodle_parameters(parameters),
        }
        try:
            with httpx.Client(timeout=self.timeout_seconds, transport=self.transport) as client:
                response = client.post(self.endpoint, data=payload)
                response.raise_for_status()
                result = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise RuntimeError("Moodle read-only API request failed") from error
        if isinstance(result, dict) and result.get("exception"):
            raise RuntimeError("Moodle rejected the read-only API request")
        return result

    def structural_snapshot(self, course_id: int) -> dict[str, Any]:
        return {
            "course": self.call("core_course_get_courses", options={"ids": [course_id]}),
            "enrolments": self.call("core_enrol_get_enrolled_users", courseid=course_id),
            "contents": self.call("core_course_get_contents", courseid=course_id),
        }


def build_oulad_controlled_export(
    prepared_dir: Path,
    *,
    learner_limit: int = 24,
    through_week: int = 12,
    exported_at: datetime | None = None,
) -> ControlledExport:
    calendar = json.loads((prepared_dir / "replay_calendar.json").read_text(encoding="utf-8"))
    start = datetime.fromisoformat(calendar["synthetic_course_start_at"]).astimezone(UTC)
    exported_at = exported_at or datetime.now(UTC)
    enrolments = list(csv.DictReader((prepared_dir / "enrolments.csv").open(encoding="utf-8")))
    selected = sorted(enrolments, key=lambda row: row["learner_id"])[:learner_limit]
    selected_ids = {row["learner_id"] for row in selected}
    records: list[dict[str, Any]] = []
    for row in selected:
        registration_day = int(row["registration_day"]) if row["registration_day"] else 0
        records.append(
            {
                "record_type": "enrolment",
                "source_record_id": f"enrolment:{row['source_record_id']}",
                "source_user_id": row["learner_id"],
                "event_code": "course_enrolled",
                "occurred_at": (start + timedelta(days=registration_day)).isoformat(),
                "available_at": (start + timedelta(days=registration_day)).isoformat(),
                "time_precision": "day",
                "value": True,
                "metadata": {
                    "replay_source": "OULAD",
                    "previous_attempts": int(row["previous_attempts"]),
                    "studied_credits": int(row["studied_credits"]),
                },
            }
        )
    through_day = through_week * 7 - 1
    with (prepared_dir / "activity_observations.csv").open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            day = int(row["course_day"])
            if row["learner_id"] not in selected_ids or day > through_day:
                continue
            records.append(
                {
                    "record_type": "event",
                    "source_record_id": f"event:{row['source_record_id']}",
                    "source_user_id": row["learner_id"],
                    "event_code": f"activity_{row['activity_group']}",
                    "occurred_at": (start + timedelta(days=day)).isoformat(),
                    "available_at": (start + timedelta(days=day)).isoformat(),
                    "time_precision": "day",
                    "count": int(row["click_count"]),
                    "metadata": {"activity_id": row["resource_id"]},
                }
            )
    with (prepared_dir / "assessment_observations.csv").open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            day = int(row["submitted_course_day"])
            if row["learner_id"] not in selected_ids or day > through_day:
                continue
            score = float(row["score"]) if row["score"] else None
            records.append(
                {
                    "record_type": "grade",
                    "source_record_id": f"grade:{row['source_record_id']}",
                    "source_user_id": row["learner_id"],
                    "event_code": "assessment_submitted",
                    "occurred_at": (start + timedelta(days=day)).isoformat(),
                    "available_at": (start + timedelta(days=day)).isoformat(),
                    "time_precision": "day",
                    "value": score,
                    "count": 1 if score is None else None,
                    "metadata": {
                        "assessment_id": row["assessment_id"],
                        "score_missing_reason": row["score_missing_reason"],
                    },
                }
            )
    records.sort(key=lambda row: (row["occurred_at"], row["source_record_id"]))
    header = ControlledExportHeader(
        source_id="moodle-replay-oulad-aaa-2030a",
        source_name="Controlled OULAD-to-Moodle replay",
        presentation_id="moodle-replay:AAA:2030A",
        module_code="AAA",
        presentation_code="2030A",
        length_days=268,
        course_start_at=start,
        exported_at=exported_at,
        scenario_id="oulad-aaa-2030a-replay-v1",
        warning=calendar["warning"],
    )
    return ControlledExport(header=header, records=records)


def _learner_id(scenario_id: str, source_user_id: str) -> str:
    digest = hashlib.sha256(f"{scenario_id}:{source_user_id}".encode()).hexdigest()[:20]
    return f"moodle-replay:learner:{digest}"


def _safe_source_record_id(raw: dict[str, Any]) -> str:
    value = raw.get("source_record_id")
    if isinstance(value, str) and 0 < len(value) <= 128:
        return value
    return f"invalid:{stable_hash(raw)[:24]}"


def _raw_cursor(raw: dict[str, Any], source_record_id: str) -> tuple[datetime, str] | None:
    value = raw.get("occurred_at")
    if not isinstance(value, (str, datetime)):
        return None
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(UTC), source_record_id


def _watermark_tuple(watermark: ReplayWatermark) -> tuple[datetime, str]:
    earliest = datetime.min.replace(tzinfo=UTC)
    return watermark.occurred_at or earliest, watermark.source_record_id or ""


def _safe_validation_errors(error: ValidationError) -> list[dict[str, Any]]:
    return [
        {"type": item["type"], "location": [str(part) for part in item["loc"]]}
        for item in error.errors(include_url=False, include_input=False)
    ]


def _flatten_moodle_parameters(
    value: dict[str, Any], prefix: str = ""
) -> dict[str, str | int | float | bool]:
    flattened: dict[str, str | int | float | bool] = {}
    for key, item in value.items():
        name = f"{prefix}[{key}]" if prefix else key
        if isinstance(item, dict):
            flattened.update(_flatten_moodle_parameters(item, name))
        elif isinstance(item, (list, tuple)):
            indexed = {str(index): nested for index, nested in enumerate(item)}
            flattened.update(
                _flatten_moodle_parameters(indexed, name)
            )
        elif item is not None:
            flattened[name] = item
    return flattened
