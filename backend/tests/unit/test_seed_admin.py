import pytest

from scripts import seed_admin


def test_admin_bootstrap_is_production_only(monkeypatch) -> None:
    monkeypatch.setattr(seed_admin.settings, "env", "development")

    with pytest.raises(SystemExit, match="production-only"):
        seed_admin.require_production_environment()


def test_admin_bootstrap_refuses_when_an_admin_already_exists() -> None:
    class ExistingAdminDatabase:
        def execute(self, _statement):
            return None

        def scalar(self, _statement):
            return "existing-admin-id"

    with pytest.raises(SystemExit, match="administrator already exists"):
        seed_admin.require_first_admin(ExistingAdminDatabase())


def test_admin_bootstrap_allows_an_empty_admin_slot() -> None:
    class EmptyDatabase:
        def execute(self, _statement):
            return None

        def scalar(self, _statement):
            return None

    seed_admin.require_first_admin(EmptyDatabase())
