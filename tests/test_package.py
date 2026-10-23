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


def test_repository_is_a_claude_plugin_exposing_the_five_skills():
    root = Path(__file__).resolve().parents[1]
    import json
    plugin = json.loads((root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert plugin["name"] == "resume-toolkit" and plugin["version"] == __version__
    skills = sorted(p.parent.name for p in (root / "skills").glob("*/SKILL.md"))
    assert skills == ["application-materials", "cover-letter-review", "experience-capture",
                      "job-search", "resume-review"]
    for name in skills:
        head = (root / "skills" / name / "SKILL.md").read_text(encoding="utf-8").split("---")[1]
        assert f"name: {name}" in head and "description:" in head
