import json
import os
import uuid
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.cli import main
from app.core.config import Settings
from app.modules.admin.domain.demo import NotEnoughOsmDataError
from app.modules.reports.domain.photos import PhotoKeys
from app.modules.reports.infrastructure.local_photo_storage import LocalPhotoStorage
from app.modules.users.domain.role import UserRole
from app.modules.validation.application.import_zones import ImportZonesResult
from app.modules.validation.domain.zones import InvalidZonesError


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


def _fake_staff_account(
    monkeypatch: pytest.MonkeyPatch, calls: list[tuple[str, str, str, UserRole]]
) -> None:
    class _CreateStaff:
        def __init__(self, *_deps: object) -> None:
            pass

        def execute(self, name: str, email: str, password: str, role: UserRole) -> uuid.UUID:
            calls.append((name, email, password, role))
            return uuid.UUID(int=7)

    monkeypatch.setattr("app.cli.create_session", nullcontext)
    monkeypatch.setattr("app.cli.CreateStaffAccount", _CreateStaff)
    monkeypatch.setattr("app.cli.SqlUserRepository", lambda _session: None)


def test_create_evaluator_creates_the_account_with_the_evaluator_role(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[tuple[str, str, str, UserRole]] = []
    _fake_staff_account(monkeypatch, calls)
    prompts: list[str] = []

    def getpass(prompt: str) -> str:
        prompts.append(prompt)
        return "una frase de paso larga"

    monkeypatch.setattr("getpass.getpass", getpass)

    assert main(["create-evaluator", "--name", "Eva", "--email", "eva@example.com"]) == 0
    assert calls == [("Eva", "eva@example.com", "una frase de paso larga", UserRole.EVALUATOR)]
    assert json.loads(capsys.readouterr().out) == {"evaluador": str(uuid.UUID(int=7))}
    assert prompts == ["Contraseña del evaluador: ", "Repite la contraseña: "]


def test_create_admin_still_creates_the_account_with_the_admin_role(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[tuple[str, str, str, UserRole]] = []
    _fake_staff_account(monkeypatch, calls)
    monkeypatch.setattr("getpass.getpass", lambda _prompt: "una frase de paso larga")

    assert main(["create-admin", "--name", "Ana", "--email", "ana@example.com"]) == 0
    assert calls[0][3] is UserRole.ADMIN
    assert json.loads(capsys.readouterr().out) == {"administrador": str(uuid.UUID(int=7))}


def test_create_evaluator_rejects_mismatched_passwords(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    answers = iter(["una frase de paso larga", "otra frase distinta"])
    monkeypatch.setattr("getpass.getpass", lambda _prompt: next(answers))

    assert main(["create-evaluator", "--name", "Eva", "--email", "eva@example.com"]) == 2
    assert "no coinciden" in capsys.readouterr().err


def test_create_evaluator_requires_name_and_email() -> None:
    with pytest.raises(SystemExit):
        main(["create-evaluator", "--email", "eva@example.com"])


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


def test_zones_import_prints_the_totals(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    received: list[object] = []

    class _UseCase:
        def execute(self, geojson: object) -> ImportZonesResult:
            received.append(geojson)
            return ImportZonesResult(zones=2, reports_assigned=9)

    file = tmp_path / "zonas.geojson"
    file.write_text('{"type": "FeatureCollection", "features": []}', encoding="utf-8")
    monkeypatch.setattr("app.cli.create_session", nullcontext)
    monkeypatch.setattr("app.cli._build_import_zones", lambda _session: _UseCase())

    assert main(["zones-import", str(file)]) == 0
    assert "Zonas cargadas: 2 · reportes asignados: 9" in capsys.readouterr().out
    assert received == [{"type": "FeatureCollection", "features": []}]


def test_zones_import_exits_1_with_the_message_when_zones_are_invalid(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    class _UseCase:
        def execute(self, geojson: object) -> object:
            raise InvalidZonesError("La zona «Centro» no es un polígono")

    file = tmp_path / "zonas.geojson"
    file.write_text("{}", encoding="utf-8")
    monkeypatch.setattr("app.cli.create_session", nullcontext)
    monkeypatch.setattr("app.cli._build_import_zones", lambda _session: _UseCase())

    assert main(["zones-import", str(file)]) == 1
    assert "La zona «Centro» no es un polígono" in capsys.readouterr().err


def test_zones_import_exits_1_when_the_file_is_missing_or_not_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    monkeypatch.setattr("app.cli.create_session", nullcontext)
    bad = tmp_path / "malo.geojson"
    bad.write_text("{no es json", encoding="utf-8")

    assert main(["zones-import", str(tmp_path / "no-existe.geojson")]) == 1
    assert "No se pudo leer" in capsys.readouterr().err
    assert main(["zones-import", str(bad)]) == 1
    assert "JSON" in capsys.readouterr().err
