import json
import os
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.cli import main
from app.core.config import Settings
from app.modules.admin.domain.demo import NotEnoughOsmDataError
from app.modules.reports.domain.photos import PhotoKeys
from app.modules.reports.infrastructure.local_photo_storage import LocalPhotoStorage


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


def test_purge_orphan_photos_prints_how_many_were_deleted(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    orphan = PhotoKeys.for_name("ab12").photo
    LocalPhotoStorage(tmp_path).save(orphan, b"jpeg")
    old = (datetime.now(UTC) - timedelta(days=1)).timestamp()
    os.utime(tmp_path / orphan, (old, old))
    monkeypatch.setattr("app.cli.get_settings", lambda: Settings(photo_storage_dir=tmp_path))
    monkeypatch.setattr("app.cli.create_session", nullcontext)
    monkeypatch.setattr("app.cli.SqlEvidenceKeys", lambda _session: _NoEvidence())

    assert main(["purge-orphan-photos"]) == 0
    assert json.loads(capsys.readouterr().out) == {"fotos_borradas": 1}
    assert not (tmp_path / orphan).exists()


class _NoEvidence:
    def referenced_photo_keys(self) -> list[str]:
        return []


class _FakeSeedDemo:
    def __init__(self, created: int = 32, error: Exception | None = None) -> None:
        self._created = created
        self._error = error
        self.calls: list[str] = []

    def execute(self) -> int:
        self.calls.append("execute")
        if self._error is not None:
            raise self._error
        return self._created

    def remove(self) -> int:
        self.calls.append("remove")
        return 32


def _use_seed(monkeypatch: pytest.MonkeyPatch, seed: _FakeSeedDemo) -> None:
    monkeypatch.setattr("app.cli.create_session", nullcontext)
    monkeypatch.setattr("app.cli._build_seed_demo", lambda _session, _settings: seed)


def test_cli_seed_demo_dispatch(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seed = _FakeSeedDemo()
    _use_seed(monkeypatch, seed)

    assert main(["seed-demo"]) == 0
    assert seed.calls == ["execute"]
    assert capsys.readouterr().out == (
        "Datos de demostración: 32 reportes creados. No son datos de campo.\n"
    )


def test_cli_seed_demo_says_when_the_data_already_exists(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _use_seed(monkeypatch, _FakeSeedDemo(created=0))

    assert main(["seed-demo"]) == 0
    assert "Ya hay datos de demostración" in capsys.readouterr().out


def test_cli_seed_demo_remove(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seed = _FakeSeedDemo()
    _use_seed(monkeypatch, seed)

    assert main(["seed-demo", "--remove"]) == 0
    assert seed.calls == ["remove"]
    assert capsys.readouterr().out == "Datos de demostración: 32 reportes borrados.\n"


def test_cli_seed_demo_without_osm_data_fails_with_a_hint(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _use_seed(monkeypatch, _FakeSeedDemo(error=NotEnoughOsmDataError("Faltan datos: osm-import")))

    assert main(["seed-demo"]) == 1
    assert "osm-import" in capsys.readouterr().err
