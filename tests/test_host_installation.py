"""Managed project integrations, using fictional data and no native host claims."""
import importlib.util
import json
from pathlib import Path

import pytest

from cv_toolkit.bootstrap import init_workspace, install_entry_hook
from cv_toolkit.records import ToolkitError


def test_managed_installer_is_available():
    assert importlib.util.find_spec('cv_toolkit.host_installation'), 'managed host installer is missing'


@pytest.fixture
def installer():
    assert importlib.util.find_spec('cv_toolkit.host_installation'), 'managed host installer is missing'
    from cv_toolkit import host_installation
    return host_installation


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "project O'Brien $literal"
    root.mkdir()
    return root


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*')
            if p.is_file() and 'install-backups' not in p.parts and '__pycache__' not in p.parts}


def install(module, project, host='codex', hooks=False):
    return module.install_agent(project / 'user-profile', host=host, project_root=project, hooks=hooks)


@pytest.mark.parametrize('host,prefix', [('codex', '.agents'), ('claude', '.claude'), ('hermes', '.hermes')])
def test_first_install_and_repeat_are_complete_and_preserve_bytes(installer, project, host, prefix):
    result = install(installer, project, host, hooks=True)
    assert result['host'] == host and result['hooks'] == 'installed'
    assert result['runtime_discovery_verified'] is False
    assert (project / prefix / 'skills/job-search/references/search-records.md').is_file()
    assert (project / '.local/resume-toolkit/installations' / (host + '.json')).is_file()
    before = snapshot(project)
    repeated = install(installer, project, host)
    assert repeated['hooks'] == 'unchanged'
    assert snapshot(project) == before


def test_existing_profile_and_owner_instructions_are_preserved(installer, project):
    init_workspace(project / 'user-profile', example='developer')
    (project / 'AGENTS.md').write_text('Owner instructions', encoding='utf-8')
    before = snapshot(project / 'user-profile')
    install(installer, project)
    assert snapshot(project / 'user-profile') == before
    assert (project / 'AGENTS.md').read_text() == 'Owner instructions'


def test_managed_skill_upgrade_updates_only_unchanged_owned_files(installer, project, monkeypatch):
    install(installer, project)
    from cv_toolkit import deployment
    original = deployment._payload
    def newer():
        payload = original()
        payload['job-search']['references/search-records.md'] += b'\nNew packaged guidance.\n'
        return payload
    monkeypatch.setattr(deployment, '_payload', newer)
    profile = snapshot(project / 'user-profile')
    assert install(installer, project)['skills'] == 'updated'
    assert 'New packaged guidance.' in (project / '.agents/skills/job-search/references/search-records.md').read_text()
    assert snapshot(project / 'user-profile') == profile
    assert list((project / '.local/resume-toolkit/install-backups').iterdir())


@pytest.mark.parametrize('change', ['edited', 'missing', 'extra'])
def test_modified_or_incomplete_skill_bundle_refuses_before_changes(installer, project, change):
    install(installer, project)
    path = project / '.agents/skills/job-search/SKILL.md'
    if change == 'edited':
        path.write_text('Owner customization', encoding='utf-8')
    elif change == 'missing':
        path.unlink()
    else:
        (path.parent / 'owner-note.md').write_text('Keep this', encoding='utf-8')
    before = snapshot(project)
    with pytest.raises(ToolkitError):
        install(installer, project)
    assert snapshot(project) == before


def test_managed_hook_code_is_refreshed_after_upgrade(installer, project, monkeypatch):
    install(installer, project, hooks=True)
    original = installer._hooks_payload
    def newer(*args):
        payload, config, groups = original(*args)
        payload['.codex/hooks/resume-toolkit/cv_toolkit/codex_hooks.py'] += b'\n# New packaged adapter\n'
        return payload, config, groups
    monkeypatch.setattr(installer, '_hooks_payload', newer)
    assert install(installer, project)['hooks'] == 'updated'
    assert (project / '.codex/hooks/resume-toolkit/cv_toolkit/codex_hooks.py').read_text().endswith('# New packaged adapter\n')


@pytest.mark.parametrize('host', ['codex', 'claude', 'hermes'])
def test_current_legacy_hook_can_be_adopted_without_rewriting(installer, project, host):
    workspace = init_workspace(project / 'user-profile')
    install_entry_hook(workspace, host, project_root=project)
    before = {p: raw for p, raw in snapshot(project).items() if p.startswith('.' + host + '/')}
    result = install(installer, project, host, hooks=True)
    assert result['hooks'] == 'unchanged'
    assert all((project / p).read_bytes() == raw for p, raw in before.items())


def test_stale_generated_startup_guide_is_reported_before_installing(installer, project):
    from cv_toolkit import deployment
    workspace = init_workspace(project / 'user-profile')
    guide = deployment._guide(workspace, project, 'codex')
    guide = guide.replace('cv_toolkit.cli', 'older_toolkit.cli')
    (project / 'RESUME_TOOLKIT.md').write_text(guide, encoding='utf-8')
    before = snapshot(project)
    with pytest.raises(ToolkitError, match='startup guide'):
        install(installer, project)
    assert snapshot(project) == before


def test_claude_upgrade_preserves_current_unrelated_settings_and_hooks(installer, project, monkeypatch):
    config = project / '.claude/settings.local.json'
    config.parent.mkdir()
    other = {'hooks': [{'type': 'command', 'command': 'owner-tool'}]}
    config.write_text(json.dumps({'permissions': {'allow': ['Read']}, 'hooks': {'SessionStart': [other]}}))
    install(installer, project, 'claude', hooks=True)
    current = json.loads(config.read_text())
    current['owner_setting'] = 'added after install'
    current['hooks']['SessionStart'].append({'hooks': [{'type': 'command', 'command': 'another-tool'}]})
    config.write_text(json.dumps(current))
    original = installer._hooks_payload
    def newer(*args):
        payload, path, groups = original(*args)
        for group in groups['SessionStart']:
            group['hooks'][0]['timeout'] = 121
        return payload, path, groups
    monkeypatch.setattr(installer, '_hooks_payload', newer)
    install(installer, project, 'claude', hooks=True)
    after = json.loads(config.read_text())
    assert after['owner_setting'] == 'added after install'
    assert after['permissions'] == {'allow': ['Read']}
    assert other in after['hooks']['SessionStart']
    assert any(group['hooks'][0].get('command') == 'another-tool' for group in after['hooks']['SessionStart'])
    assert sum(group['hooks'][0].get('timeout') == 121 for group in after['hooks']['SessionStart']) == 1


def test_modified_owned_hook_group_refuses_upgrade(installer, project):
    install(installer, project, 'claude', hooks=True)
    config = project / '.claude/settings.local.json'
    current = json.loads(config.read_text())
    current['hooks']['SessionStart'][0]['hooks'][0]['timeout'] = 999
    config.write_text(json.dumps(current))
    before = snapshot(project)
    with pytest.raises(ToolkitError):
        install(installer, project, 'claude', hooks=True)
    assert snapshot(project) == before


def test_inventory_cannot_authorize_arbitrary_profile_writes(installer, project):
    install(installer, project)
    manifest = project / '.local/resume-toolkit/installations/codex.json'
    record = json.loads(manifest.read_text())
    record['files']['user-profile/profile/evidence.json'] = '0' * 64
    manifest.write_text(json.dumps(record))
    before = snapshot(project)
    with pytest.raises(ToolkitError):
        install(installer, project)
    assert snapshot(project) == before


def test_inventory_cannot_claim_an_unrelated_owner_hook(installer, project):
    config = project / '.claude/settings.local.json'
    config.parent.mkdir()
    owner = {'hooks': [{'type': 'command', 'command': 'owner-tool'}]}
    config.write_text(json.dumps({'hooks': {'SessionStart': [owner]}}))
    install(installer, project, 'claude', hooks=True)
    manifest = project / '.local/resume-toolkit/installations/claude.json'
    record = json.loads(manifest.read_text())
    record['configs']['.claude/settings.local.json']['SessionStart'].append(owner)
    manifest.write_text(json.dumps(record))
    before = snapshot(project)
    with pytest.raises(ToolkitError):
        install(installer, project, 'claude', hooks=True)
    assert snapshot(project) == before


def test_conflicting_binding_is_not_rebound(installer, project):
    install(installer, project)
    before = snapshot(project)
    with pytest.raises(ToolkitError):
        installer.install_agent(project / 'another-profile', host='claude', project_root=project)
    assert snapshot(project) == before


def test_failure_restores_written_integration_files(installer, project, monkeypatch):
    original = installer._write_bytes
    def fail_one(path, raw):
        if path.name == 'codex_hooks.py' and 'install-backups' not in path.parts:
            raise OSError('simulated disk failure')
        return original(path, raw)
    monkeypatch.setattr(installer, '_write_bytes', fail_one)
    with pytest.raises((ToolkitError, OSError)):
        install(installer, project, hooks=True)
    assert not list((project / '.agents').rglob('SKILL.md'))
    assert not (project / '.local/resume-toolkit/installations/codex.json').exists()


def test_rollback_preserves_a_concurrent_owner_edit(installer, project, monkeypatch):
    original = installer._write_bytes
    owner_path = project / '.agents/skills/application-materials/SKILL.md'
    def conflicting_write(path, raw):
        if path.name == 'codex_hooks.py' and 'install-backups' not in path.parts:
            owner_path.write_text('New owner edit during install', encoding='utf-8')
            raise OSError('simulated later failure')
        return original(path, raw)
    monkeypatch.setattr(installer, '_write_bytes', conflicting_write)
    with pytest.raises((ToolkitError, OSError)):
        install(installer, project, hooks=True)
    assert owner_path.read_text() == 'New owner edit during install'


def test_sequential_hosts_share_profile_without_enabling_unrequested_hooks(installer, project):
    for host in ('codex', 'claude', 'hermes'):
        result = install(installer, project, host)
        assert result['hooks'] == 'not_requested'
    assert not (project / '.codex/hooks.json').exists()
    assert not (project / '.claude/settings.local.json').exists()
    assert not (project / '.hermes/plugins/resume-toolkit').exists()


def test_upgrade_reports_other_hosts_that_need_refresh(installer, project, monkeypatch):
    from cv_toolkit import deployment
    install(installer, project, 'codex')
    install(installer, project, 'claude')
    original = deployment._payload
    def newer():
        result = original()
        result['job-search']['references/search-records.md'] += b'\nUpdated package\n'
        return result
    monkeypatch.setattr(deployment, '_payload', newer)
    assert install(installer, project, 'codex')['other_hosts_needing_attention'] == ['claude']
    assert install(installer, project, 'claude')['other_hosts_needing_attention'] == []


def test_symlinked_integration_directory_is_rejected(installer, project, tmp_path):
    external = tmp_path / 'external'
    external.mkdir()
    try:
        (project / '.agents').symlink_to(external, target_is_directory=True)
    except OSError:
        pytest.skip('symlink creation unavailable')
    with pytest.raises(ToolkitError):
        install(installer, project)
    assert not list(external.iterdir())
