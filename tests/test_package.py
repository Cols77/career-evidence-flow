from cv_toolkit import __version__
from pathlib import Path
import tomllib


def test_package_exposes_version():
    assert __version__ == "0.2.0"


def test_neutral_distribution_preserves_console_entrypoint():
    manifest = Path(__file__).resolve().parents[1] / "pyproject.toml"
    project = tomllib.loads(manifest.read_text(encoding="utf-8"))["project"]
    assert project["name"] == "resume-toolkit"
    assert project["scripts"]["cv"] == "cv_toolkit.cli:main"
    assert project["version"] == __version__
    assert project["readme"] == "README.md"
    assert "urls" not in project
    assert "build>=1.2" in project["optional-dependencies"]["dev"]
