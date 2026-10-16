import pytest

from app.cli import main


def test_osm_import_rejects_invalid_bbox(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["osm-import", "--bbox", "1,2,3"]) == 2
    assert "Área inválida" in capsys.readouterr().err


def test_unknown_command_exits_with_usage_error() -> None:
    with pytest.raises(SystemExit):
        main(["no-existe"])
