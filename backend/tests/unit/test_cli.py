import pytest

from app.cli import main


def test_osm_import_rejects_invalid_bbox(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["osm-import", "--bbox", "1,2,3"]) == 2
    assert "Área inválida" in capsys.readouterr().err


def test_unknown_command_exits_with_usage_error() -> None:
    with pytest.raises(SystemExit):
        main(["no-existe"])


def test_create_admin_rejects_mismatched_passwords(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    answers = iter(["una frase de paso larga", "otra frase distinta"])
    monkeypatch.setattr("getpass.getpass", lambda _prompt: next(answers))

    assert main(["create-admin", "--name", "Admin", "--email", "admin@example.com"]) == 2
    assert "no coinciden" in capsys.readouterr().err


def test_create_admin_requires_name_and_email() -> None:
    with pytest.raises(SystemExit):
        main(["create-admin", "--email", "admin@example.com"])
