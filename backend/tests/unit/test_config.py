from app.core.config import Environment, Settings


def test_database_url_uses_psycopg_driver_and_env_values() -> None:
    settings = Settings(
        postgres_user="u",
        postgres_password="p@ss",
        postgres_host="db",
        postgres_port=5433,
        postgres_db="streetrepo",
    )

    assert settings.database_url == "postgresql+psycopg://u:p%40ss@db:5433/streetrepo"


def test_cors_origins_are_split_and_trimmed() -> None:
    settings = Settings(cors_origins=" http://a.test , http://b.test ,, ")

    assert settings.cors_origin_list == ["http://a.test", "http://b.test"]


def test_empty_cors_origins_allows_none() -> None:
    assert Settings(cors_origins="").cors_origin_list == []


def test_password_is_not_exposed_in_repr() -> None:
    assert "secreto" not in repr(Settings(postgres_password="secreto"))


def test_is_production_only_for_prod() -> None:
    assert Settings(app_env=Environment.PROD).is_production
    assert not Settings(app_env=Environment.DEV).is_production
