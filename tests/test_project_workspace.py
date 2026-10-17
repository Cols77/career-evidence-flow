"""Explicit project discovery roots keep the ordinary candidate data schema."""
import json
from pathlib import Path
import sys
import subprocess
import shutil

import pytest

from cv_toolkit.bootstrap import SKILLS, init_workspace
from cv_toolkit.cli import main


def invoke(capsys, *args):
    try:
        code = main(list(args))
    except SystemExit as exc:
        pytest.fail(f'Project workspace command is unavailable: {exc}')
    return code, json.loads(capsys.readouterr().out)


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in root.rglob('*') if p.is_file()}


def test_setup_binds_nested_standard_workspace_to_project_hosts(tmp_path, capsys):
    project = tmp_path / 'project with spaces'
    project.mkdir()
    workspace = project / 'user-profile'
    (project / 'AGENTS.md').write_text('Existing project instructions', encoding='utf-8')
    (project / 'CLAUDE.md').write_text('Existing Claude instructions', encoding='utf-8')
    other = project / '.agents/skills/other/SKILL.md'
    other.parent.mkdir(parents=True)
    other.write_text('Unrelated skill', encoding='utf-8')
    before = snapshot(project)
    args = ('setup', str(workspace), '--host', 'all', '--project-root', str(project))
    code, result = invoke(capsys, *args)
    assert code == 0
    assert result['workspace'] == str(workspace.resolve())
    assert result['project_root'] == str(project.resolve())
    assert json.loads((project / '.local/resume-toolkit/project.json').read_text()) == {
        'schema_version': 1, 'workspace': 'user-profile'}
    assert json.loads((workspace / 'profile/evidence.json').read_text()) == {
        'schema_version': '1', 'candidate_id': 'candidate.new', 'items': []}
    assert not (project / 'cvtool.toml').exists()
    for prefix in ('.agents/skills', '.claude/skills', '.hermes/skills'):
        for skill in SKILLS:
            assert (project / prefix / skill / 'SKILL.md').is_file()
        assert not (workspace / prefix).exists()
    for path, content in before.items():
        assert (project / path).read_bytes() == content
    guide = (project / 'RESUME_TOOLKIT.md').read_text(encoding='utf-8')
    assert str(workspace.resolve()) in guide
    assert str(Path(sys.executable).resolve()) in guide
    assert 'cv_toolkit.cli' in guide
    assert '--project-root' in guide
    installed = snapshot(project)
    assert invoke(capsys, *args)[0] == 0
    assert snapshot(project) == installed


def test_doctor_checks_project_skills_and_nested_data_without_writes(tmp_path, capsys):
    workspace = tmp_path / 'user-profile'
    assert invoke(capsys, 'setup', str(workspace), '--host', 'all', '--project-root', str(tmp_path))[0] == 0
    before = snapshot(tmp_path)
    code, result = invoke(capsys, 'doctor', '--workspace', str(workspace), '--host', 'all', '--project-root', str(tmp_path))
    assert code == 0
    checks = {entry['id']: entry for entry in result['checks']}
    assert checks['workspace']['status'] == 'pass'
    assert all(checks[f'skills.{host}']['status'] == 'pass' for host in ('codex', 'claude', 'hermes'))
    assert result['project_root'] == str(tmp_path.resolve())
    assert result['runtime_discovery_verified'] is False
    assert checks['package']['path'] == str(Path(__import__('cv_toolkit').__file__).resolve().parent)
    assert snapshot(tmp_path) == before
    # Without explicit binding, the same invocation must not silently use parent skills.
    assert invoke(capsys, 'doctor', '--workspace', str(workspace), '--host', 'all')[0] == 2


@pytest.mark.parametrize('command', ['setup', 'doctor', 'install-skills'])
def test_external_workspace_binding_is_rejected_without_writes(tmp_path, capsys, command):
    project = tmp_path / 'project'
    project.mkdir()
    workspace = init_workspace(tmp_path / 'external')
    before = snapshot(tmp_path)
    args = [command, str(workspace)] if command == 'setup' else [command, '--workspace', str(workspace)]
    code, result = invoke(capsys, *args, '--host', 'codex', '--project-root', str(project))
    assert code == 2
    assert result['status'] == 'invalid'
    assert snapshot(tmp_path) == before


def test_symlink_workspace_escape_is_rejected(tmp_path, capsys):
    project = tmp_path / 'project'
    project.mkdir()
    outside = init_workspace(tmp_path / 'outside')
    alias = project / 'user-profile'
    try:
        alias.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip('Directory symlinks unavailable')
    before = snapshot(tmp_path)
    assert invoke(capsys, 'setup', str(alias), '--host', 'all', '--project-root', str(project))[0] == 2
    assert snapshot(tmp_path) == before


def test_install_skills_uses_explicit_project_root(tmp_path, capsys):
    workspace = init_workspace(tmp_path / 'user-profile')
    code, result = invoke(capsys, 'install-skills', '--workspace', str(workspace), '--host', 'codex', '--project-root', str(tmp_path))
    assert code == 0
    assert result['skill_count'] == len(SKILLS)
    assert (tmp_path / '.agents/skills/experience-capture/SKILL.md').is_file()
    assert not (workspace / '.agents').exists()


def test_project_skill_conflict_does_not_initialize_nested_workspace(tmp_path, capsys):
    conflict = tmp_path / '.agents/skills/experience-capture/SKILL.md'
    conflict.parent.mkdir(parents=True)
    conflict.write_text('Owner customization', encoding='utf-8')
    before = snapshot(tmp_path)
    workspace = tmp_path / 'user-profile'
    code, result = invoke(capsys, 'setup', str(workspace), '--host', 'all', '--project-root', str(tmp_path))
    assert code == 2
    assert 'conflict' in result['error']
    assert not workspace.exists()
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize('command', ['setup', 'doctor', 'install-skills'])
def test_existing_project_binding_rejects_another_workspace_without_writes(tmp_path, capsys, command):
    workspace = tmp_path / 'user-profile'
    assert invoke(capsys, 'setup', str(workspace), '--host', 'codex', '--project-root', str(tmp_path))[0] == 0
    other = init_workspace(tmp_path / 'another-profile')
    before = snapshot(tmp_path)
    args = [command, str(other)] if command == 'setup' else [command, '--workspace', str(other)]
    code, result = invoke(capsys, *args, '--host', 'claude', '--project-root', str(tmp_path))
    assert code == 2
    assert 'binding' in result['error'].lower()
    assert snapshot(tmp_path) == before


def test_malformed_project_binding_is_not_overwritten(tmp_path, capsys):
    binding = tmp_path / '.local/resume-toolkit/project.json'
    binding.parent.mkdir(parents=True)
    binding.write_text('{"workspace":"elsewhere"}', encoding='utf-8')
    before = snapshot(tmp_path)
    code, result = invoke(capsys, 'setup', str(tmp_path / 'user-profile'), '--host', 'codex', '--project-root', str(tmp_path))
    assert code == 2
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize('obstruction', ['.local', '.local/resume-toolkit'])
def test_binding_parent_file_is_rejected_before_workspace_initialization(tmp_path, capsys, obstruction):
    path = tmp_path / obstruction
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('Preserve this file', encoding='utf-8')
    before = snapshot(tmp_path)
    workspace = tmp_path / 'user-profile'
    assert invoke(capsys, 'setup', str(workspace), '--host', 'all', '--project-root', str(tmp_path))[0] == 2
    assert not workspace.exists()
    assert snapshot(tmp_path) == before


def test_existing_generated_guide_for_other_workspace_blocks_first_binding(tmp_path, capsys):
    guide = tmp_path / 'RESUME_TOOLKIT.md'
    guide.write_text('# Resume Toolkit workspace\n\nData workspace: `another-workspace`\n', encoding='utf-8')
    before = snapshot(tmp_path)
    workspace = tmp_path / 'user-profile'
    code, result = invoke(capsys, 'setup', str(workspace), '--host', 'all', '--project-root', str(tmp_path))
    assert code == 2
    assert 'guide' in result['error'].lower()
    assert not workspace.exists()
    assert snapshot(tmp_path) == before


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows junction contract')
@pytest.mark.parametrize('command', ['doctor', 'install-skills'])
def test_retargeted_in_project_workspace_binding_is_rejected(tmp_path, capsys, command):
    workspace = tmp_path / 'user-profile'
    assert invoke(capsys, 'setup', str(workspace), '--host', 'codex', '--project-root', str(tmp_path))[0] == 0
    workspace.rename(tmp_path / 'original-profile')
    other = init_workspace(tmp_path / 'other-profile')
    result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(workspace), str(other)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    try:
        before = snapshot(other)
        host = 'claude' if command == 'install-skills' else 'codex'
        code, result = invoke(capsys, command, '--workspace', str(workspace), '--host', host,
                              '--project-root', str(tmp_path))
        assert code == 2
        assert 'binding' in result['error'].lower()
        assert snapshot(other) == before
    finally:
        workspace.rmdir()  # The junction itself only; do not recurse into data.


@pytest.mark.parametrize('problem', ['unignored', 'tracked', 'ignored'])
@pytest.mark.skipif(shutil.which('git') is None, reason='Git is needed to verify private workspace ignores')
def test_split_doctor_checks_whole_candidate_workspace_privacy(tmp_path, capsys, problem):
    workspace = tmp_path / 'user-profile'
    assert invoke(capsys, 'setup', str(workspace), '--host', 'codex', '--project-root', str(tmp_path))[0] == 0
    subprocess.run(['git', 'init', str(tmp_path)], check=True, capture_output=True)
    if problem in ('tracked', 'ignored'):
        (tmp_path / '.gitignore').write_text('/user-profile/\n', encoding='utf-8')
    if problem == 'tracked':
        subprocess.run(['git', '-C', str(tmp_path), 'add', '-f', 'user-profile/profile/evidence.json'],
                       check=True, capture_output=True)
    code, result = invoke(capsys, 'doctor', '--workspace', str(workspace), '--host', 'codex',
                          '--project-root', str(tmp_path))
    assert code == (0 if problem == 'ignored' else 2)
    check = next(check for check in result['checks'] if check['id'] == 'workspace_ignore')
    assert check['status'] == ('pass' if problem == 'ignored' else 'error')
    assert check['enforced'] is (problem == 'ignored')


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows junction contract')
def test_project_host_junction_conflict_preflights_before_profile_initialization(tmp_path, capsys):
    target = tmp_path / '.claude'
    target.mkdir()
    alias = tmp_path / '.agents'
    result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(alias), str(target)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    try:
        workspace = tmp_path / 'user-profile'
        code, result = invoke(capsys, 'setup', str(workspace), '--host', 'all',
                              '--project-root', str(tmp_path))
        assert code == 2
        assert not workspace.exists()
        assert not list(target.iterdir())
        assert not (tmp_path / '.local').exists()
    finally:
        alias.rmdir()


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows junction contract')
def test_install_skills_rejects_in_project_discovery_alias(tmp_path, capsys):
    workspace = init_workspace(tmp_path / 'user-profile')
    target = tmp_path / 'aliased-host'
    target.mkdir()
    alias = tmp_path / '.agents'
    result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(alias), str(target)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    try:
        code, _ = invoke(capsys, 'install-skills', '--workspace', str(workspace), '--host', 'codex',
                         '--project-root', str(tmp_path))
        assert code == 2
        assert not list(target.iterdir())
    finally:
        alias.rmdir()
