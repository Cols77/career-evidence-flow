"""Portable setup preserves private records and diagnoses rather than enabling hosts."""
from importlib.resources import files
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from cv_toolkit.bootstrap import SKILLS, init_workspace
from cv_toolkit.cli import main


PREFIXES = {'codex': '.agents/skills', 'claude': '.claude/skills', 'hermes': '.hermes/skills'}


def run_cli(capsys, *arguments):
    try:
        code = main(list(arguments))
    except SystemExit as exc:
        pytest.fail(f'CLI does not support the requested deployment command: {exc}')
    return code, json.loads(capsys.readouterr().out)


def snapshot(root):
    return {path.relative_to(root).as_posix(): (path.read_bytes(), path.stat().st_mtime_ns)
            for path in root.rglob('*') if path.is_file()}


@pytest.mark.parametrize('host', PREFIXES)
def test_setup_installs_only_requested_complete_host_and_routes_empty_profile(tmp_path, capsys, host):
    root = tmp_path / 'private workspace'
    code, result = run_cli(capsys, 'setup', str(root), '--host', host, '--name', 'Example Person')
    assert code == 0
    assert result['state'] == 'missing_candidate'
    assert result['skill'] == 'experience-capture'
    assert result['runtime_discovery_verified'] is False
    assert json.loads((root / 'profile/evidence.json').read_text())['items'] == []
    for candidate, prefix in PREFIXES.items():
        assert (root / prefix).exists() == (candidate == host)
    for name in SKILLS:
        expected = files('cv_toolkit').joinpath('assets', 'skills', name)
        actual = root / PREFIXES[host] / name
        assert (actual / 'SKILL.md').read_bytes() == expected.joinpath('SKILL.md').read_bytes()
        assert list((actual / 'references').rglob('*.md'))
    assert (root / 'RESUME_TOOLKIT.md').is_file()
    assert not (root / '.codex').exists()
    assert not (root / '.hermes/plugins').exists()


def test_all_host_setup_is_idempotent_and_preserves_real_profile_and_instructions(tmp_path, capsys):
    root = init_workspace(tmp_path / 'existing', example='developer')
    evidence_path = root / 'profile/evidence.json'
    evidence = json.loads(evidence_path.read_text())
    evidence['candidate_id'] = 'candidate.user-provided'
    evidence_path.write_text(json.dumps(evidence), encoding='utf-8')
    (root / 'AGENTS.md').write_bytes(b'Owner instructions\r\n')
    (root / 'CLAUDE.md').write_bytes(b'Owner Claude instructions\r\n')
    before = snapshot(root)
    code, result = run_cli(capsys, 'setup', str(root), '--host', 'all', '--name', 'Ignored Name')
    assert code == 0
    for relative, record in before.items():
        assert snapshot(root)[relative] == record
    assert result['instructions']['AGENTS.md'] == 'preserved'
    assert result['instructions']['CLAUDE.md'] == 'preserved'
    assert result['startup_guide'].endswith('RESUME_TOOLKIT.md')
    installed = snapshot(root)
    code, repeated = run_cli(capsys, 'setup', str(root), '--host', 'all')
    assert code == 0
    assert snapshot(root) == installed
    assert all(record['skills'] == 'unchanged' for record in repeated['hosts'].values())


@pytest.mark.parametrize('damage', ['changed', 'partial', 'extra'])
def test_conflict_in_last_host_preflights_every_host_without_writing(tmp_path, capsys, damage):
    root = tmp_path / 'workspace'
    assert run_cli(capsys, 'setup', str(root), '--host', 'hermes')[0] == 0
    skill = root / '.hermes/skills' / SKILLS[-1]
    if damage == 'changed':
        (skill / 'SKILL.md').write_bytes(b'Custom user policy')
    elif damage == 'partial':
        (skill / 'SKILL.md').unlink()
    else:
        (skill / 'custom.md').write_bytes(b'Owner additions')
    before = snapshot(root)
    code, result = run_cli(capsys, 'setup', str(root), '--host', 'all')
    assert code == 2
    assert 'conflict' in result['error'].lower()
    assert 'backup' in result['error'].lower() or 'back up' in result['error'].lower()
    assert snapshot(root) == before
    assert not (root / '.agents').exists()
    assert not (root / '.claude').exists()


def test_partial_host_bundle_is_not_silently_completed(tmp_path, capsys):
    root = tmp_path / 'workspace'
    assert run_cli(capsys, 'setup', str(root), '--host', 'codex')[0] == 0
    shutil.rmtree(root / '.agents/skills' / SKILLS[-1])
    before = snapshot(root)
    code, result = run_cli(capsys, 'setup', str(root), '--host', 'codex')
    assert code == 2
    assert 'conflict' in result['error'].lower()
    assert snapshot(root) == before


@pytest.mark.parametrize('kind', ['unconfigured', 'malformed'])
def test_setup_refuses_nonempty_invalid_workspace_without_writes(tmp_path, capsys, kind):
    root = tmp_path / 'workspace'
    root.mkdir()
    (root / ('cvtool.toml' if kind == 'malformed' else 'owner.txt')).write_text('preserve', encoding='utf-8')
    before = snapshot(root)
    code, result = run_cli(capsys, 'setup', str(root), '--host', 'all')
    assert code == 2
    assert result['error']
    assert snapshot(root) == before


def test_setup_synthetic_example_stays_demonstration_and_does_not_replace_existing_profile(tmp_path, capsys):
    root = tmp_path / 'demo'
    args = ('setup', str(root), '--host', 'all', '--example', 'showcase')
    code, result = run_cli(capsys, *args)
    assert code == 0
    assert result['state'] == 'synthetic'
    assert (root / 'resume.md').is_file()
    before = snapshot(root)
    code, result = run_cli(capsys, *args)
    assert code == 2
    assert '--example' in result['error']
    assert snapshot(root) == before
    assert run_cli(capsys, 'setup', str(root), '--host', 'all')[0] == 0
    assert snapshot(root) == before


def test_setup_does_not_claim_existing_hooks_are_disabled(tmp_path, capsys):
    root = init_workspace(tmp_path / 'workspace')
    hooks = root / '.codex/hooks.json'
    hooks.parent.mkdir()
    hooks.write_bytes(b'{"hooks": {"SessionStart": []}}\n')
    before = hooks.read_bytes(), hooks.stat().st_mtime_ns
    code, result = run_cli(capsys, 'setup', str(root), '--host', 'all')
    assert code == 0
    assert 'hooks_enabled' not in result
    assert result['hooks_changed'] is False
    assert result['hooks_installed_by_setup'] is False
    assert (hooks.read_bytes(), hooks.stat().st_mtime_ns) == before


@pytest.mark.parametrize('profile', ['empty', 'synthetic'])
def test_setup_and_doctor_validate_records_even_before_real_candidate_capture(tmp_path, capsys, profile):
    root = init_workspace(tmp_path / 'workspace', example='developer' if profile == 'synthetic' else None)
    (root / 'profile/registry.json').write_text('[{"invalid": true}]', encoding='utf-8')
    before = snapshot(root)
    assert run_cli(capsys, 'setup', str(root), '--host', 'all')[0] == 2
    code, result = run_cli(capsys, 'doctor', '--workspace', str(root))
    assert code == 2
    assert result['state'] == 'malformed'
    assert result['skill'] == ''
    assert any(check['id'] == 'workspace' and check['status'] == 'error' for check in result['checks'])
    assert snapshot(root) == before


def test_malformed_projection_in_empty_profile_is_not_ignored_by_setup_or_doctor(tmp_path, capsys):
    root = tmp_path / 'workspace'
    assert run_cli(capsys, 'setup', str(root), '--host', 'codex')[0] == 0
    (root / 'profile/projection.json').write_text('{}', encoding='utf-8')
    before = snapshot(root)
    code, result = run_cli(capsys, 'doctor', '--workspace', str(root), '--host', 'codex')
    assert code == 2
    assert result['state'] == 'malformed'
    assert result['skill'] == ''
    assert run_cli(capsys, 'setup', str(root), '--host', 'all')[0] == 2
    assert snapshot(root) == before


def test_doctor_is_read_only_with_explicit_warnings_and_no_runtime_claims(tmp_path, capsys, monkeypatch):
    root = tmp_path / 'workspace'
    assert run_cli(capsys, 'setup', str(root), '--host', 'all')[0] == 0
    before = snapshot(root)
    monkeypatch.setattr('cv_toolkit.deployment.shutil.which', lambda _: None)
    monkeypatch.setattr('cv_toolkit.render._find_chromium', lambda: None)
    code, result = run_cli(capsys, 'doctor', '--workspace', str(root))
    assert code == 0  # Missing optional prerequisites do not invalidate an empty profile.
    assert result['state'] == 'missing_candidate'
    assert result['runtime_discovery_verified'] is False
    assert result['hook_execution_verified'] is False
    assert result['independent_review_verified'] is False
    checks = {item['id']: item for item in result['checks']}
    assert checks['browser']['status'] == 'warning'
    assert checks['cli.codex']['status'] == 'warning'
    assert checks['output_ignore']['enforced'] is False
    assert checks['output_ignore']['rule_present'] is True
    assert snapshot(root) == before


@pytest.mark.parametrize('kind', ['missing', 'malformed', 'skill-conflict'])
def test_doctor_returns_useful_nonzero_diagnostics_without_repairs(tmp_path, capsys, kind):
    root = tmp_path / 'workspace'
    if kind != 'missing':
        assert run_cli(capsys, 'setup', str(root), '--host', 'codex')[0] == 0
        if kind == 'malformed':
            (root / 'profile/evidence.json').write_text('{}', encoding='utf-8')
        else:
            (root / '.agents/skills/resume-review/SKILL.md').write_text('changed', encoding='utf-8')
    before = snapshot(root)
    code, result = run_cli(capsys, 'doctor', '--workspace', str(root), '--host', 'codex')
    assert code == 2
    assert any(check['status'] == 'error' for check in result['checks'])
    assert snapshot(root) == before
    assert root.exists() == (kind != 'missing')


@pytest.mark.skipif(shutil.which('git') is None, reason='Git is needed to verify ignore enforcement')
def test_doctor_checks_configured_output_directory_and_git_tracking(tmp_path, capsys):
    root = tmp_path / 'workspace'
    assert run_cli(capsys, 'setup', str(root), '--host', 'codex')[0] == 0
    config = root / 'cvtool.toml'
    config.write_text(config.read_text().replace('outputs = "outputs"', 'outputs = "generated"'), encoding='utf-8')
    (root / '.gitignore').write_text('generated/\n', encoding='utf-8')
    subprocess.run(['git', 'init', str(root)], check=True, capture_output=True)
    before = snapshot(root)
    code, result = run_cli(capsys, 'doctor', '--workspace', str(root), '--host', 'codex')
    assert code == 0
    check = next(item for item in result['checks'] if item['id'] == 'output_ignore')
    assert check['enforced'] is True
    assert check['status'] == 'pass'
    assert snapshot(root) == before
    output = root / 'generated/resume.pdf'
    output.parent.mkdir()
    output.write_bytes(b'fictional preview')
    subprocess.run(['git', '-C', str(root), 'add', '-f', 'generated/resume.pdf'], check=True, capture_output=True)
    code, result = run_cli(capsys, 'doctor', '--workspace', str(root), '--host', 'codex')
    assert code == 2
    check = next(item for item in result['checks'] if item['id'] == 'output_ignore')
    assert check['status'] == 'error'
    assert check['tracked_output_count'] == 1


@pytest.mark.skipif(shutil.which('git') is None, reason='Git is needed for root discovery')
def test_doctor_warns_when_hermes_skills_are_below_git_project_root(tmp_path, capsys):
    subprocess.run(['git', 'init', str(tmp_path)], check=True, capture_output=True)
    root = tmp_path / 'nested workspace'
    assert run_cli(capsys, 'setup', str(root), '--host', 'hermes')[0] == 0
    before = snapshot(root)
    code, result = run_cli(capsys, 'doctor', '--workspace', str(root), '--host', 'hermes')
    assert code == 0
    check = next(item for item in result['checks'] if item['id'] == 'hermes.project_root')
    assert check['status'] == 'warning'
    assert 'root' in check['message']
    assert result['runtime_discovery_verified'] is False
    assert snapshot(root) == before
