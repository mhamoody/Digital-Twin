"""Course-scoped client for the version-two instructor workspace."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from .client import DashboardApiClient


def _course_path(presentation_id: str) -> str:
    return f"/api/v2/courses/{quote(presentation_id, safe=':')}"


class WorkspaceClient(DashboardApiClient):
    """Reuse the signed dashboard transport; never connect to storage directly."""

    def courses(self) -> dict[str, Any]:
        return self._request("GET", "/api/v2/courses")

    def workspace(
        self,
        presentation_id: str,
        *,
        week: int,
        query: str = "",
        risk: str = "",
        status: str = "",
        offset: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        return self._request(
            "GET",
            f"{_course_path(presentation_id)}/workspace",
            params={
                "week": week,
                "query": query,
                "risk": risk,
                "status": status,
                "offset": offset,
                "limit": limit,
            },
        )

    def learner(self, presentation_id: str, learner_id: str, *, week: int) -> dict[str, Any]:
        return self._request(
            "GET",
            f"{_course_path(presentation_id)}/learners/{quote(learner_id, safe=':')}",
            params={"week": week},
        )

    def save_policy(self, presentation_id: str, policy: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", f"{_course_path(presentation_id)}/policy", json=policy)

    def save_case(
        self,
        presentation_id: str,
        learner_id: str,
        payload: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"{_course_path(presentation_id)}/learners/{quote(learner_id, safe=':')}/case",
            headers={**self.headers, "Idempotency-Key": idempotency_key},
            json=payload,
        )

    def analyze(
        self,
        presentation_id: str,
        *,
        week: int,
        model_kind: str = "llm",
        learner_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"week": week, "model_kind": model_kind}
        if learner_ids is not None:
            payload["learner_ids"] = learner_ids
        return self._request("POST", f"{_course_path(presentation_id)}/analysis", json=payload)

    def model_status(self) -> dict[str, Any]:
        return self._request("GET", "/api/v2/model/status")
