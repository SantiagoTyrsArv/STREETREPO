import re
import tomllib
from pathlib import Path

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
