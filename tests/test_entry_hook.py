"""Installation and real-Hermes dispatch of the state-aware entry hook.

The dispatch test loads the installed project plugin through Hermes' real
plugin manager (discovery + register + ``pre_llm_call`` invocation) inside a
temporary ``HERMES_HOME`` with the project-plugin opt-in. It costs no model API
calls — the hook is invoked directly on the manager, the same way the agent
emits ``pre_llm_call`` every turn. It skips when no Hermes installation is
findable so unrelated CI can still pass.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from cv_toolkit.bootstrap import HOOK_NAME, install_entry_hook
from cv_toolkit.records import ToolkitError

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def test_install_hook_writes_manifest_and_copies_classifier(tmp_path):
    count = install_entry_hook(tmp_path, "hermes")
    folder = tmp_path / ".hermes/plugins" / HOOK_NAME
    assert count == len([p for p in folder.rglob('*') if p.is_file()])
    assert (folder / "plugin.yaml").is_file()
    assert (folder / "__init__.py").is_file()
    installed = folder / "onboarding.py"
    assert installed.is_file()
    # Classifier is a verbatim copy of the canonical module (single source).
    canonical = (ROOT / "src/cv_toolkit/onboarding.py").read_bytes()
    assert installed.read_bytes() == canonical


def test_install_hook_refuses_overwrite_and_leaves_existing(tmp_path):
    folder = tmp_path / ".hermes/plugins" / HOOK_NAME
    folder.mkdir(parents=True)
    sentinel = folder / "owner.md"
    sentinel.write_text("user additions", encoding="utf-8")
    with pytest.raises(ToolkitError):
        install_entry_hook(tmp_path, "hermes")
    assert sentinel.read_text(encoding="utf-8") == "user additions"
    assert not (folder / "plugin.yaml").exists()


def test_install_hook_rejects_other_hosts(tmp_path):
    with pytest.raises(ToolkitError):
        install_entry_hook(tmp_path, "claude")
    assert not (tmp_path / ".hermes/plugins" / HOOK_NAME).exists()


@pytest.fixture
def hermes_python():
    """Locate a Hermes python; skip the dispatch test if none is found."""
    candidates = [
        os.environ.get("HERMES_PYTHON"),
        str(Path.home() / "AppData/Local/hermes/hermes-agent/venv/Scripts/python.exe"),
        str(Path.home() / ".hermes/hermes-agent/venv/bin/python"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    pytest.skip("no Hermes installation found to dispatch against")


def _dispatch_driver():
    """Return a small driver that discovers project plugins and fires pre_llm_call."""
    return (
        "import json\n"
        "from hermes_cli.plugins import get_plugin_manager\n"
        "from hermes_cli.lifecycle import invoke_hook\n"
        "from agent.turn_context import compose_user_api_content\n"
        "m = get_plugin_manager()\n"
        "m.discover_and_load(force=True)\n"
        "results = invoke_hook(\n"
        "    'pre_llm_call', session_id='test', user_message='hi',\n"
        "    conversation_history=[], is_first_turn=True, model='m', platform='cli',\n"
        "    telemetry_schema_version=1)\n"
        "print('DISPATCH=' + json.dumps(results))\n"
        "context = '\\n'.join(r['context'] for r in results if isinstance(r, dict) and r.get('context'))\n"
        "print('API_CONTENT=' + json.dumps(compose_user_api_content('hi', '', context)))\n"
    )


def test_real_hermes_dispatch_routes_workspace_state(
    tmp_path, hermes_python, monkeypatch
):
    # A private toolkit workspace with empty default candidate -> interview/import.
    from cv_toolkit.bootstrap import init_workspace
    from cv_toolkit.onboarding import classify

    ws = init_workspace(tmp_path / "ws", name="Candidate")
    install_entry_hook(tmp_path / "ws", "hermes")

    home = tmp_path / "home"
    home.mkdir()
    (home / "config.yaml").write_text(
        f"plugins:\n  enabled:\n    - {HOOK_NAME}\n", encoding="utf-8"
    )

    env = dict(os.environ)
    env["HERMES_HOME"] = str(home)
    env["HERMES_ENABLE_PROJECT_PLUGINS"] = "1"
    # Exercise the self-contained installed bundle, not checkout imports.
    env.pop('PYTHONPATH', None)

    driver = tmp_path / "driver.py"
    driver.write_text(_dispatch_driver(), encoding="utf-8")

    # Sanity: the classifier on this workspace yields the expected routing.
    assert classify(ws).state == "missing_candidate"

    proc = subprocess.run(
        [hermes_python, str(driver)],
        cwd=str(ws),  # discovery reads ./.hermes/plugins relative to cwd
        env=env, capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    line = next((l for l in proc.stdout.splitlines() if l.startswith("DISPATCH=")), None)
    assert line, f"no dispatch output; stdout={proc.stdout!r} stderr={proc.stderr!r}"
    results = json.loads(line[len("DISPATCH="):])
    found = [r for r in results if isinstance(r, dict) and r.get("context")]
    assert found, f"pre_llm_call returned no context: {results!r}"
    context = found[0]["context"]
    assert "experience-capture" in context
    assert "INTERVIEW" in context or "interview" in context.lower()
    api_line = next(l for l in proc.stdout.splitlines() if l.startswith('API_CONTENT='))
    api_content = json.loads(api_line[len('API_CONTENT='):])
    assert 'experience-capture' in api_content
    assert 'hi' in api_content


def test_real_hermes_dispatch_ready_steers_to_application(
    tmp_path, hermes_python
):
    from cv_toolkit.bootstrap import init_workspace

    ws = init_workspace(tmp_path / "ws", name="Ana")
    evidence = {
        "schema_version": "1", "candidate_id": "candidate.ana",
        "items": [{"id": "item.e", "kind": "experience", "claims": [
            {"id": "claim.c", "text": "T", "status": "confirmed",
             "publication": "allowed", "sources": ["source.owner"]}]}],
    }
    registry = [{"source_id": "source.owner", "kind": "owner_supplied", "fingerprint": "v1"}]
    projection = {"schema_version": 1, "id": "projection.p", "label": "Ana",
                  "sections": [{"id": "section.s", "label": "E",
                                "item_ids": ["item.e"], "claim_ids": ["claim.c"]}]}
    for rel in ("profile/evidence.json", "profile/registry.json", "profile/projection.json"):
        (ws / rel).parent.mkdir(parents=True, exist_ok=True)
        (ws / rel).write_text(
            json.dumps({"profile/evidence.json": evidence,
                        "profile/registry.json": registry,
                        "profile/projection.json": projection}[rel]), encoding="utf-8")
    install_entry_hook(ws, "hermes")

    home = tmp_path / "home"; home.mkdir()
    (home / "config.yaml").write_text(
        f"plugins:\n  enabled:\n    - {HOOK_NAME}\n", encoding="utf-8")

    driver = tmp_path / "driver.py"
    driver.write_text(_dispatch_driver(), encoding="utf-8")
    env = dict(os.environ)
    env["HERMES_HOME"] = str(home)
    env["HERMES_ENABLE_PROJECT_PLUGINS"] = "1"
    env.pop('PYTHONPATH', None)

    proc = subprocess.run([hermes_python, str(driver)], cwd=str(ws), env=env,
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr
    line = next((l for l in proc.stdout.splitlines() if l.startswith("DISPATCH=")), None)
    assert line, proc.stdout
    results = json.loads(line[len("DISPATCH="):])
    found = [r for r in results if isinstance(r, dict) and r.get("context")]
    assert found, results
    assert "application-materials" in found[0]["context"]
    api_line = next(l for l in proc.stdout.splitlines() if l.startswith('API_CONTENT='))
    assert 'application-materials' in json.loads(api_line[len('API_CONTENT='):])


def _load_installed_plugin(root):
    import importlib.util
    folder = root / '.hermes/plugins' / HOOK_NAME
    spec = importlib.util.spec_from_file_location(
        '_test_resume_hook', folder / '__init__.py',
        submodule_search_locations=[str(folder)])
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_hook_routes_setup_and_stays_silent_outside_scope(tmp_path, monkeypatch):
    root = tmp_path / 'project'
    root.mkdir()
    install_entry_hook(root, 'hermes')
    module = _load_installed_plugin(root)
    monkeypatch.chdir(root)
    assert 'private workspace' in module._route(platform='cli')['context']
    assert module._route(platform='telegram') is None
    monkeypatch.chdir(tmp_path)
    assert module._route(platform='cli') is None


def test_hook_error_is_visible_and_ready_routes_on_later_turn(tmp_path, monkeypatch):
    install_entry_hook(tmp_path, 'hermes')
    module = _load_installed_plugin(tmp_path)
    monkeypatch.chdir(tmp_path)
    def broken(root):
        raise RuntimeError('PRIVATE CONTENT SHOULD NEVER BE ECHOED')
    monkeypatch.setattr(module.onboarding, 'classify', broken)
    result = module._route(platform='cli')['context']
    assert 'could not be validated' in result
    assert 'PRIVATE CONTENT' not in result
    from types import SimpleNamespace
    monkeypatch.setattr(module.onboarding, 'classify', lambda root: SimpleNamespace(
        as_context=lambda: {'context': 'application-materials'}))
    assert 'application-materials' in module._route(platform='cli', is_first_turn=False)['context']


@pytest.mark.parametrize('payload', [{}, {'platform': None}, {'platform': ''},
                                    {'platform': 'desktop'}, {'platform': 'gateway'}])
def test_hook_requires_explicit_cli_before_reading_records(tmp_path, monkeypatch, payload):
    install_entry_hook(tmp_path, 'hermes')
    module = _load_installed_plugin(tmp_path)
    monkeypatch.chdir(tmp_path)
    reads = []
    monkeypatch.setattr(module.onboarding, 'classify', lambda root: reads.append(root))
    assert module._route(**payload) is None
    assert reads == []
