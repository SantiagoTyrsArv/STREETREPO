import json
import os
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.cli import main
from app.core.config import Settings
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
