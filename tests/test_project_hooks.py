"""Project discovery roots may bind one explicit contained data workspace."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from cv_toolkit.bootstrap import init_workspace, install_entry_hook
from cv_toolkit import codex_hooks
from cv_toolkit.records import ToolkitError


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "project O'Brien $literal"
    root.mkdir()
    init_workspace(root / 'user-profile')
    return root


def payload(cwd, event='SessionStart'):
    return {'hook_event_name': event, 'cwd': str(cwd), 'session_id': 'synthetic.session'}


def run_bundle(project, host, workspace, data):
    runner = project / f'.{host}/hooks/resume-toolkit/run.py'
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    return subprocess.run([sys.executable, '-I', str(runner), '--workspace', str(workspace)],
                          input=json.dumps(data), capture_output=True, text=True,
                          cwd=project.parent, env=env, timeout=30)


def test_codex_project_cwd_routes_pinned_child_and_stores_state_only_there(project):
    workspace = project / 'user-profile'
    install_entry_hook(workspace, 'codex', project_root=project)
    result = run_bundle(project, 'codex', workspace, payload(project))
    assert result.returncode == 0, result.stderr
    context = json.loads(result.stdout)['hookSpecificOutput']['additionalContext']
    assert 'experience-capture' in context and str(workspace) in context
    assert list((workspace / '.codex/resume-toolkit/sessions').glob('*.json'))
    assert not (project / '.codex/resume-toolkit').exists()


def test_codex_project_binding_rejects_other_workspaces_and_override(project):
    workspace = project / 'user-profile'
    other = init_workspace(project / 'other-profile')
    nested = init_workspace(workspace / 'nested-profile')
    install_entry_hook(workspace, 'codex', project_root=project)
    for cwd in (other, nested, project.parent):
        result = run_bundle(project, 'codex', workspace, payload(cwd))
        assert json.loads(result.stdout) == {}
    result = run_bundle(project, 'codex', other, payload(project))
    assert 'systemMessage' in json.loads(result.stdout)
    assert not (other / '.codex').exists()


def test_codex_project_root_keeps_checkpoint_after_compaction(project):
    workspace = project / 'user-profile'
    codex_hooks.record_checkpoint(workspace, 'synthetic.session', 'resume-review', 'working', [])
    result = codex_hooks.dispatch({**payload(project), 'source': 'compact'}, workspace, project_root=project)
    assert 'resume-review' in result['hookSpecificOutput']['additionalContext']


def load_hermes(project):
    folder = project / '.hermes/plugins/resume-toolkit'
    spec = importlib.util.spec_from_file_location('_project_hook_test', folder / '__init__.py',
                                                submodule_search_locations=[str(folder)])
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_hermes_project_routes_pinned_child_only_at_project_cli_cwd(project, monkeypatch):
    workspace = project / 'user-profile'
    install_entry_hook(workspace, 'hermes', project_root=project)
    module = load_hermes(project)
    monkeypatch.chdir(project)
    context = module._route(platform='cli')['context']
    assert 'experience-capture' in context and str(workspace) in context
    assert str(project / '.hermes/skills') in context
    assert module._route(platform='desktop') is None
    monkeypatch.chdir(workspace)
    assert module._route(platform='cli') is None


@pytest.mark.parametrize('host', ['codex', 'claude', 'hermes'])
def test_hook_install_rejects_external_data_without_writing_project(project, tmp_path, host):
    external = init_workspace(tmp_path / 'outside')
    before = set(project.rglob('*'))
    with pytest.raises(ToolkitError):
        install_entry_hook(external, host, project_root=project)
    assert set(project.rglob('*')) == before


@pytest.mark.parametrize('event', ['SessionStart', 'UserPromptSubmit'])
def test_claude_installed_runner_routes_project_with_no_profile_mutations(project, event):
    workspace = project / 'user-profile'
    before = {p.relative_to(workspace): p.read_bytes() for p in workspace.rglob('*') if p.is_file()}
    count = install_entry_hook(workspace, 'claude', project_root=project)
    config = json.loads((project / '.claude/settings.local.json').read_text())
    assert set(config['hooks']) == {'SessionStart', 'UserPromptSubmit'}
    assert count > 1
    handler = config['hooks'][event][0]['hooks'][0]
    assert handler['args'][0] == '-I'
    proc = subprocess.run([handler['command'], *handler['args']], input=json.dumps(payload(project, event)),
                          capture_output=True, text=True, cwd=project.parent, timeout=30)
    assert proc.returncode == 0 and proc.stderr == ''
    context = json.loads(proc.stdout)['hookSpecificOutput']['additionalContext']
    assert 'experience-capture' in context and str(workspace) in context
    assert 'advisory' in context and 'preview' in context
    assert before == {p.relative_to(workspace): p.read_bytes() for p in workspace.rglob('*') if p.is_file()}


def test_claude_preserves_existing_settings_and_hooks(project):
    config_path = project / '.claude/settings.local.json'
    config_path.parent.mkdir()
    existing_hook = {'hooks': [{'type': 'command', 'command': 'existing-owner-command'}]}
    existing = {'permissions': {'allow': ['Read']}, 'hooks': {'SessionStart': [existing_hook], 'Stop': []}}
    config_path.write_text(json.dumps(existing))
    install_entry_hook(project / 'user-profile', 'claude', project_root=project)
    actual = json.loads(config_path.read_text())
    assert actual['permissions'] == existing['permissions']
    assert actual['hooks']['SessionStart'][0] == existing_hook
    assert len(actual['hooks']['SessionStart']) == 2
    assert actual['hooks']['Stop'] == []
    before = config_path.read_bytes()
    with pytest.raises(ToolkitError):
        install_entry_hook(project / 'user-profile', 'claude', project_root=project)
    assert config_path.read_bytes() == before


@pytest.mark.parametrize('raw', ['[]', '{bad', '{"hooks": []}', '{"hooks":{"SessionStart":{}}}'])
def test_claude_rejects_invalid_existing_settings_without_bundle(project, raw):
    config_path = project / '.claude/settings.local.json'
    config_path.parent.mkdir()
    config_path.write_text(raw)
    with pytest.raises(ToolkitError):
        install_entry_hook(project / 'user-profile', 'claude', project_root=project)
    assert config_path.read_text() == raw
    assert not (project / '.claude/hooks/resume-toolkit').exists()


def test_claude_rejects_foreign_nested_and_missing_session_payloads(project):
    workspace = project / 'user-profile'
    nested = init_workspace(workspace / 'nested')
    sibling = init_workspace(project / 'other-profile')
    install_entry_hook(workspace, 'claude', project_root=project)
    for data in (payload(nested), payload(sibling), payload(project.parent),
                 {**payload(project), 'session_id': ''}, payload(project, 'Stop')):
        result = run_bundle(project, 'claude', workspace, data)
        assert json.loads(result.stdout) == {}


def test_claude_malformed_input_is_bounded_and_sanitized(project):
    workspace = project / 'user-profile'
    install_entry_hook(workspace, 'claude', project_root=project)
    runner = project / '.claude/hooks/resume-toolkit/run.py'
    for raw in ('{PRIVATE', 'x' * 256001):
        result = subprocess.run([sys.executable, '-I', str(runner), '--workspace', str(workspace)],
                                input=raw, text=True, capture_output=True, timeout=30)
        assert result.returncode == 0
        assert 'systemMessage' in json.loads(result.stdout)
        assert 'PRIVATE' not in result.stdout + result.stderr


@pytest.mark.parametrize('host', ['codex', 'claude'])
@pytest.mark.skipif(sys.platform != 'win32', reason='Windows junction contract')
def test_installed_binding_rejects_retargeted_data_junction(project, host):
    workspace = project / 'user-profile'
    install_entry_hook(workspace, host, project_root=project)
    original = project / 'original-profile'
    workspace.rename(original)
    other = init_workspace(project / 'other-profile')
    proc = subprocess.run(['cmd', '/c', 'mklink', '/J', str(workspace), str(other)],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    try:
        result = run_bundle(project, host, workspace, payload(project))
        assert 'systemMessage' in json.loads(result.stdout)
        assert not (other / '.codex').exists()
        assert not (other / '.claude').exists()
    finally:
        workspace.rmdir()  # Remove the junction only; never recurse into its target.


def test_claude_same_root_default_remains_supported(tmp_path):
    workspace = init_workspace(tmp_path / 'profile')
    install_entry_hook(workspace, 'claude')
    result = run_bundle(workspace, 'claude', workspace, payload(workspace))
    assert 'experience-capture' in json.loads(result.stdout)['hookSpecificOutput']['additionalContext']
