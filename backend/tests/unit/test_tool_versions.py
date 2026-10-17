import re
import tomllib
from pathlib import Path

from app import __version__

REPO_DIR = Path(__file__).resolve().parents[3]
PYPROJECT = REPO_DIR / "backend" / "pyproject.toml"
API_DOCKERFILE = REPO_DIR / "infra" / "docker" / "api.Dockerfile"


def test_dockerfile_uses_the_uv_version_required_by_pyproject() -> None:
    # La CI toma la versión de `required-version` (setup-uv); Dependabot solo actualiza el
    # Dockerfile, así que esta prueba avisa cuando hay que subir también pyproject.toml.
    required = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["tool"]["uv"][
        "required-version"
    ]
    image = re.search(r"^FROM ghcr\.io/astral-sh/uv:(\S+)", API_DOCKERFILE.read_text(), re.M)

    assert image is not None
    assert required == f"=={image.group(1)}"


def test_app_version_matches_pyproject() -> None:
    # La imagen no incluye pyproject.toml ni el proyecto se instala como paquete, así que la
    # versión vive en app/__init__.py; esta prueba impide que se separen (decisión 30a).
    project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]

    assert __version__ == project["version"]
