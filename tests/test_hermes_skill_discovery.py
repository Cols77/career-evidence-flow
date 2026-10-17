"""Real-Hermes discovery of the workspace's installed project skills.

The project ships five canonical skills (``cv_toolkit.bootstrap.SKILLS``) that
are installed into ``<root>/.hermes/skills/`` by ``install_skills``.  These
resume-toolkit skills are *project* skills in Hermes' native discovery model
(``agent.skill_utils``): they load only when the process runs inside the git
checkout and that checkout is listed under ``skills.trusted_project_dirs`` in
``config.yaml``.

These acceptance tests exercise the *real* installed Hermes discovery stack
(``tools.skills_tool`` + ``agent.skill_utils``) in a bounded subprocess with
an isolated ``HERMES_HOME`` and an isolated process cwd — never touching the
user's real profile or trust state, making no model-API/paid calls, and
reading no credentials.  Each test skips when no Hermes installation is
findable (the same convention as ``test_entry_hook.py``) so unrelated CI can
still pass.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from cv_toolkit.bootstrap import SKILLS, install_skills

HERE = Path(__file__).resolve().parent

CANONICAL = set(SKILLS)
# A stable marker present in the installed experience-capture SKILL.md body.
MAIN_MARKER = "You are the interviewer"
# A stable marker present in its linked reference file.
REF_MARKER = "Evidence and interview reference"


@pytest.fixture
def hermes_python():
    """Locate a Hermes python; skip the discovery tests if none is found."""
    candidates = [
        os.environ.get("HERMES_PYTHON"),
        str(Path.home() / "AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe"),
        str(Path.home() / ".hermes/hermes-agent/venv/bin/python"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    pytest.skip("no Hermes installation found to dispatch against")


@pytest.fixture
def non_git_tmp_path():
    """Keep the no-project case outside any enclosing checkout or --basetemp."""
    # pytest's basetemp may intentionally live in the project, and even a sibling
    # under a coding directory can inherit that directory's .git marker.
    with tempfile.TemporaryDirectory(prefix='resume-toolkit-no-git-') as directory:
        root = Path(directory).resolve()
        enclosing = [str(parent) for parent in (root, *root.parents)
                     if (parent / '.git').exists()]
        assert not enclosing, f'No-Git fixture requires an OS temp directory outside repositories: {enclosing}'
        yield root


def _home_with_config(tmp_path, *, trusted_repo=None, disable=False):
    """Create an isolated HERMES_HOME with a skills config block."""
    home = tmp_path / "hermes-home"
    home.mkdir()
    (home / "skills").mkdir(parents=True, exist_ok=True)
    lines = ["skills:", "  external_dirs: []"]
    if disable:
        lines.append("  project_discovery: false")
    if trusted_repo is not None:
        # Forward-slash form so the absolute path survives YAML quoting.
        repo_path = str(trusted_repo).replace("\\", "/")
        lines.append(f"  trusted_project_dirs: ['{repo_path}']")
    (home / "config.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return home


def _git_repo(tmp_path, name):
    """A directory carrying the `.git` marker Hermes uses as the project root."""
    repo = tmp_path / name
    repo.mkdir(parents=True)
    (repo / ".git").mkdir(parents=True, exist_ok=True)
    return repo


# One driver exercises every surface; each test asserts on the lines it owns.
_DRIVER = (
    "import json, sys\n"
    "from tools.skills_tool import skills_list, skill_view\n"
    "from agent import skill_utils as su\n"
    "\n"
    "root = su.find_project_root()\n"
    "print('PROJECT_ROOT=' + json.dumps(str(root) if root is not None else None))\n"
    "names = sorted(s['name'] for s in json.loads(skills_list()).get('skills', []))\n"
    "print('LIST_NAMES=' + json.dumps(names))\n"
    "print('PROJECT_DIRS=' + json.dumps([str(d) for d in su.get_project_skills_dirs()]))\n"
    "ut = su.get_untrusted_project_skills_root()\n"
    "print('UNTRUSTED=' + json.dumps({'none': ut is None, 'count': ut[1] if ut else 0}))\n"
    "\n"
    "main = json.loads(skill_view('experience-capture'))\n"
    "print('VIEW_MAIN=' + json.dumps({\n"
    "    'success': main.get('success'),\n"
    "    'source_path': main.get('_source_path'),\n"
    "    'has_marker': '%s' in str(main.get('content', '')),\n"
    "}))\n"
    "ref = json.loads(skill_view('experience-capture', file_path='references/evidence-and-interview.md'))\n"
    "print('VIEW_REF=' + json.dumps({\n"
    "    'success': ref.get('success'),\n"
    "    'source_path': ref.get('_source_path'),\n"
    "    'file': ref.get('file'),\n"
    "    'has_marker': '%s' in str(ref.get('content', '')),\n"
    "    'is_binary': bool(ref.get('is_binary')),\n"
    "}))\n"
) % (MAIN_MARKER, REF_MARKER)


def _bounded_run(hermes_python, tmp_path, driver, *, home, cwd, timeout=120):
    """Run a small driver against the hermes python with isolated home + cwd."""
    script = tmp_path / "driver.py"
    script.write_text(driver, encoding="utf-8")
    env = dict(os.environ)
    env["HERMES_HOME"] = str(home)
    # Isolate: drop checkout/test imports and any surface workdir inheritance,
    # so project resolution is driven purely by the subprocess cwd.
    env.pop("PYTHONPATH", None)
    env.pop("TERMINAL_CWD", None)
    return subprocess.run(
        [hermes_python, str(script)],
        cwd=str(cwd), env=env, capture_output=True, text=True, timeout=timeout,
    )


def _line(proc, prefix):
    return next(
        (l for l in proc.stdout.splitlines() if l.startswith(prefix)), None
    )


def _install_all(root):
    # installs the genuine packaged skill assets under <root>/.hermes/skills/.
    install_skills(root, "hermes")


def test_installed_workspace_skills_are_discovered(tmp_path, hermes_python):
    """Trusted git checkout: the installed project skills show up in skills_list."""
    repo = _git_repo(tmp_path, "repo")
    _install_all(repo)
    home = _home_with_config(tmp_path, trusted_repo=repo)
    proc = _bounded_run(hermes_python, tmp_path, _DRIVER, home=home, cwd=repo)
    assert proc.returncode == 0, proc.stderr
    names = json.loads(_line(proc, "LIST_NAMES=")[len("LIST_NAMES="):])
    assert CANONICAL <= set(names), f"missing project skills; got {names}"
    dirs = json.loads(_line(proc, "PROJECT_DIRS=")[len("PROJECT_DIRS="):])
    assert any(".hermes" in d and "skills" in d for d in dirs)


def test_skill_view_loads_main_and_linked_reference(tmp_path, hermes_python):
    """Trusted git checkout: skill_view returns SKILL.md and a linked reference."""
    repo = _git_repo(tmp_path, "repo")
    _install_all(repo)
    home = _home_with_config(tmp_path, trusted_repo=repo)
    proc = _bounded_run(hermes_python, tmp_path, _DRIVER, home=home, cwd=repo)
    assert proc.returncode == 0, proc.stderr

    main = json.loads(_line(proc, "VIEW_MAIN=")[len("VIEW_MAIN="):])
    assert main["success"] is True, main
    assert main["has_marker"] is True, main
    installed = repo / '.hermes/skills/experience-capture'
    assert Path(main['source_path']).resolve() == (installed / 'SKILL.md').resolve()

    ref = json.loads(_line(proc, "VIEW_REF=")[len("VIEW_REF="):])
    assert ref["success"] is True, ref
    assert ref["file"] == "references/evidence-and-interview.md", ref
    assert ref["has_marker"] is True, ref
    assert ref["is_binary"] is False
    assert Path(ref['source_path']).resolve() == (installed / 'references/evidence-and-interview.md').resolve()


def test_untrusted_project_skills_do_not_load(tmp_path, hermes_python):
    """Git checkout NOT trusted: skills hidden and skill_view reports not found."""
    repo = _git_repo(tmp_path, "repo")
    _install_all(repo)
    home = _home_with_config(tmp_path, trusted_repo=None)  # not trusted
    proc = _bounded_run(hermes_python, tmp_path, _DRIVER, home=home, cwd=repo)
    assert proc.returncode == 0, proc.stderr

    names = json.loads(_line(proc, "LIST_NAMES=")[len("LIST_NAMES="):])
    assert CANONICAL.isdisjoint(set(names)), f"untrusted skills leaked: {names}"
    assert json.loads(_line(proc, "PROJECT_DIRS=")[len("PROJECT_DIRS="):]) == []

    main = json.loads(_line(proc, "VIEW_MAIN=")[len("VIEW_MAIN="):])
    assert main["success"] is False and main["has_marker"] is False, main

    untrusted = json.loads(_line(proc, "UNTRUSTED=")[len("UNTRUSTED="):])
    assert untrusted["none"] is False and untrusted["count"] >= len(CANONICAL), untrusted


def test_no_git_project_discovery_has_no_fallback(non_git_tmp_path, hermes_python):
    """Skills next to a non-git cwd are not picked up: no accidental fallback."""
    tmp_path = non_git_tmp_path
    plain = tmp_path / "plain"  # no .git marker anywhere up from it
    plain.mkdir(parents=True)
    _install_all(plain)
    home = _home_with_config(tmp_path, trusted_repo=plain)
    proc = _bounded_run(hermes_python, tmp_path, _DRIVER, home=home, cwd=plain)
    assert proc.returncode == 0, proc.stderr
    assert json.loads(_line(proc, 'PROJECT_ROOT=')[len('PROJECT_ROOT='):]) is None

    names = json.loads(_line(proc, "LIST_NAMES=")[len("LIST_NAMES="):])
    assert CANONICAL.isdisjoint(set(names)), f"repo-local skills loaded sans git: {names}"
    assert json.loads(_line(proc, "PROJECT_DIRS=")[len("PROJECT_DIRS="):]) == []
    untrusted = json.loads(_line(proc, "UNTRUSTED=")[len("UNTRUSTED="):])
    assert untrusted["none"] is True, untrusted
