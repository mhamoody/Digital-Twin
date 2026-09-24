import pytest

from digital_twin.dashboard.auth import AccountConfigurationError, development_account_from_env


def clear_auth(monkeypatch):
    for key in (
        "DIGITAL_TWIN_AUTH_FILE",
        "DIGITAL_TWIN_DEVELOPMENT_AUTH",
        "DIGITAL_TWIN_DASHBOARD_ID",
        "DIGITAL_TWIN_DASHBOARD_ROLE",
        "DIGITAL_TWIN_PRESENTATION_ID",
    ):
        monkeypatch.delenv(key, raising=False)


def test_development_identity_can_be_constructed_when_auth_file_is_present(monkeypatch):
    clear_auth(monkeypatch)
    monkeypatch.setenv("DIGITAL_TWIN_AUTH_FILE", "var/auth/instructors.json")
    monkeypatch.setenv("DIGITAL_TWIN_DEVELOPMENT_AUTH", "1")
    monkeypatch.setenv("DIGITAL_TWIN_DASHBOARD_ID", "instructor:dashboard-demo")
    monkeypatch.setenv("DIGITAL_TWIN_DASHBOARD_ROLE", "instructor")
    monkeypatch.setenv("DIGITAL_TWIN_PRESENTATION_ID", "validation:DEMO:2026")
    account = development_account_from_env()
    assert account.reviewer_id == "instructor:dashboard-demo"


def test_development_auth_requires_explicit_flag(monkeypatch):
    clear_auth(monkeypatch)
    monkeypatch.setenv("DIGITAL_TWIN_DASHBOARD_ID", "instructor:dashboard-demo")
    monkeypatch.setenv("DIGITAL_TWIN_DASHBOARD_ROLE", "instructor")
    monkeypatch.setenv("DIGITAL_TWIN_PRESENTATION_ID", "validation:DEMO:2026")
    assert development_account_from_env() is None


@pytest.mark.parametrize(("role", "identity"), [("instructor", "supervisor:dashboard-demo"), ("supervisor", "instructor:dashboard-demo")])
def test_development_identity_role_must_match(monkeypatch, role, identity):
    clear_auth(monkeypatch)
    monkeypatch.setenv("DIGITAL_TWIN_DEVELOPMENT_AUTH", "1")
    monkeypatch.setenv("DIGITAL_TWIN_DASHBOARD_ROLE", role)
    monkeypatch.setenv("DIGITAL_TWIN_DASHBOARD_ID", identity)
    monkeypatch.setenv("DIGITAL_TWIN_PRESENTATION_ID", "validation:DEMO:2026")
    with pytest.raises(AccountConfigurationError):
        development_account_from_env()


@pytest.mark.parametrize("role", ["instructor", "supervisor"])
def test_development_identity_is_scoped(monkeypatch, role):
    clear_auth(monkeypatch)
    monkeypatch.setenv("DIGITAL_TWIN_DEVELOPMENT_AUTH", "1")
    monkeypatch.setenv("DIGITAL_TWIN_DASHBOARD_ROLE", role)
    monkeypatch.setenv("DIGITAL_TWIN_DASHBOARD_ID", f"{role}:dashboard-demo")
    monkeypatch.setenv("DIGITAL_TWIN_PRESENTATION_ID", "validation:DEMO:2026")
    account = development_account_from_env()
    assert account.reviewer_id == f"{role}:dashboard-demo"
    assert account.allowed_presentations == ("validation:DEMO:2026",)
