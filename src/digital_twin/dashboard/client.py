"""Small API-only client used by the Streamlit instructor dashboard."""

from __future__ import annotations

from typing import Any

import httpx


class DashboardApiError(RuntimeError):
    """A safe, displayable dashboard/API boundary failure."""


class DashboardApiClient:
    def __init__(
        self,
        *,
        base_url: str,
        instructor_id: str,
        instructor_role: str,
        timeout_seconds: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        parsed_url = httpx.URL(base_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.host:
            raise ValueError("API URL must be an absolute HTTP(S) URL")
        if instructor_role not in {"instructor", "supervisor"}:
            raise ValueError("dashboard role must be instructor or supervisor")
        self.base_url = str(parsed_url).rstrip("/")
        self.headers = {
            "X-Instructor-ID": instructor_id,
            "X-Instructor-Role": instructor_role,
        }
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    def readiness(self) -> dict[str, Any]:
        return self._request("GET", "/health/ready", authenticated=False)

    def presentation_overview(self, presentation_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/presentations/{presentation_id}/overview")

    def learners(
        self,
        *,
        presentation_id: str,
        query: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> dict[str, Any]:
        params: dict[str, str | int] = {"limit": limit, "offset": offset}
        if query:
            params["query"] = query
        return self._request(
            "GET", f"/api/v1/presentations/{presentation_id}/learners", params=params
        )

    def learner_detail(self, *, presentation_id: str, learner_id: str) -> dict[str, Any]:
        return self._request(
            "GET", f"/api/v1/presentations/{presentation_id}/learners/{learner_id}"
        )

    def alerts(
        self,
        *,
        presentation_id: str,
        status: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> dict[str, Any]:
        params: dict[str, str | int] = {
            "presentation_id": presentation_id,
            "limit": limit,
            "offset": offset,
        }
        if status:
            params["status"] = status
        return self._request("GET", "/api/v1/alerts", params=params)

    def alert_detail(self, alert_id: str) -> dict[str, Any]:
        return self._request("GET", f"/api/v1/alerts/{alert_id}")

    def review_alert(
        self,
        *,
        alert_id: str,
        new_status: str,
        note: str | None,
        idempotency_key: str,
    ) -> dict[str, Any]:
        headers = {**self.headers, "Idempotency-Key": idempotency_key}
        return self._request(
            "POST",
            f"/api/v1/alerts/{alert_id}/reviews",
            headers=headers,
            json={"new_status": new_status, "note": note or None},
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        authenticated: bool = True,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        request_headers = (
            headers if headers is not None else (self.headers if authenticated else {})
        )
        try:
            with httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = client.request(method, path, headers=request_headers, **kwargs)
                response.raise_for_status()
                payload = response.json()
        except httpx.TimeoutException as error:
            raise DashboardApiError("The instructor API timed out. Try Refresh data.") from error
        except httpx.HTTPStatusError as error:
            if error.response.status_code in {401, 403}:
                message = "Dashboard identity was rejected by the instructor API."
            elif error.response.status_code == 404:
                message = "The requested course or alert was not found."
            elif error.response.status_code == 409:
                message = "That review conflicts with the current alert status. Refresh data."
            else:
                message = "The instructor API returned an error. Try Refresh data."
            raise DashboardApiError(message) from error
        except (httpx.RequestError, ValueError) as error:
            raise DashboardApiError(
                "The instructor API is unavailable. Check its status."
            ) from error
        if not isinstance(payload, dict):
            raise DashboardApiError("The instructor API returned an invalid response.")
        return payload
