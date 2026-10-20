"""Keep legacy support courses distinct from the rich course workspace."""

from collections.abc import Iterable

from .client import DashboardApiClient, DashboardApiError


def legacy_support_courses(
    client: DashboardApiClient, allowed_presentations: Iterable[str]
) -> list[str]:
    """Use the authorized API, never infer backend availability from an ID prefix.

    A v2-only course is not necessarily imported into legacy support tables.
    Hide only genuinely absent courses; authorization/service errors must surface.
    """
    available = []
    for presentation in dict.fromkeys(allowed_presentations):
        try:
            client.presentation_overview(presentation)
        except DashboardApiError as error:
            if error.status_code != 404:
                raise
        else:
            available.append(presentation)
    return available
