import importlib.util
import json
from pathlib import Path
import subprocess

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / 'tools' / 'check_shareable.py'


def module():
    spec = importlib.util.spec_from_file_location('shareability', SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git(repo, *args):
    result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, check=True)
    return result.stdout


@pytest.fixture
def scan_repo(tmp_path):
    repo = tmp_path / 'project'
    repo.mkdir()
    git(repo, 'init', '-b', 'main')
    git(repo, 'config', 'user.name', 'Fixture Author')
    git(repo, 'config', 'user.email', 'fixture@example.invalid')
    denylist = tmp_path / 'private.json'
    denylist.write_text(json.dumps({'rules': [{'id': 'private.fixture', 'token': 'Secret Fixture Identity'}]}))
    return repo, denylist


def test_staged_scan_works_before_first_commit_and_never_echoes_match(scan_repo):
    repo, denylist = scan_repo
    (repo / 'README.md').write_text('Secret Fixture Identity')
    git(repo, 'add', 'README.md')
    result = module().scan(repo, denylist, 'staged')
    assert result['status'] == 'blocked'
    assert result['findings'] == [{'path': 'README.md', 'rule_id': 'private.fixture'}]
    assert 'Secret Fixture Identity' not in json.dumps(result)
    (repo / 'README.md').write_text('Neutral toolkit')
    git(repo, 'add', 'README.md')
    assert module().scan(repo, denylist, 'staged')['status'] == 'ok'


def test_history_scans_deleted_bytes_and_author_metadata(scan_repo):
    repo, denylist = scan_repo
    (repo / 'README.md').write_text('Secret Fixture Identity')
    git(repo, 'add', '.')
    git(repo, 'commit', '-m', 'neutral')
    (repo / 'README.md').write_text('clean now')
    git(repo, 'add', '.')
    git(repo, 'commit', '-m', 'clean')
    result = module().scan(repo, denylist, 'history')
    assert {'path': 'README.md', 'rule_id': 'private.fixture'} in result['findings']
    git(repo, '-c', 'user.name=Secret Fixture Identity', 'commit', '--allow-empty', '-m', 'metadata')
    assert {'path': '<commit-metadata>', 'rule_id': 'private.fixture'} in module().scan(repo, denylist, 'history')['findings']


def test_tags_and_commit_messages_are_scanned(scan_repo):
    repo, denylist = scan_repo
    (repo / 'safe.txt').write_text('neutral')
    git(repo, 'add', '.')
    git(repo, 'commit', '-m', 'neutral')
    git(repo, 'tag', '-a', 'release', '-m', 'Secret Fixture Identity')
    assert {'path': '<tag-metadata>', 'rule_id': 'private.fixture'} in module().scan(repo, denylist, 'history')['findings']


@pytest.mark.parametrize('content', ['{}', '{"rules":[]}', 'broken', '{"rules":[{"id":"x","token":""}]}'])
def test_invalid_denylist_fails_closed(scan_repo, content):
    repo, denylist = scan_repo
    denylist.write_text(content)
    report = module().scan(repo, denylist, 'worktree')
    assert report['status'] == 'blocked'
    assert 'Secret Fixture Identity' not in json.dumps(report)


def test_internal_denylist_missing_denylist_and_git_failure_fail_closed(scan_repo):
    repo, denylist = scan_repo
    internal = repo / 'private.json'
    internal.write_bytes(denylist.read_bytes())
    assert module().scan(repo, internal, 'worktree')['status'] == 'blocked'
    assert module().scan(repo, repo.parent / 'missing', 'staged')['status'] == 'blocked'
    assert module().scan(repo.parent, denylist, 'worktree')['status'] == 'blocked'
    assert module().scan(repo, denylist, 'history')['status'] == 'blocked'


def test_sensitive_paths_binary_and_utf16_are_detected(scan_repo):
    repo, denylist = scan_repo
    (repo / '.env').write_text('not read as a secret')
    (repo / 'data.bin').write_bytes(b'\x00\xff\x01')
    (repo / 'memo.txt').write_bytes('secret fixture identity'.encode('utf-16'))
    git(repo, 'add', '.')
    result = module().scan(repo, denylist, 'staged')
    assert {'path': '.env', 'rule_id': 'sensitive.path'} in result['findings']
    assert {'path': 'data.bin', 'rule_id': 'unexpected.binary'} in result['findings']
    assert {'path': 'memo.txt', 'rule_id': 'private.fixture'} in result['findings']


def test_forced_staging_of_ignored_user_profile_is_blocked(scan_repo):
    repo, denylist = scan_repo
    (repo / '.gitignore').write_text('/user-profile/\n')
    candidate = repo / 'user-profile' / 'profile' / 'evidence.json'
    candidate.parent.mkdir(parents=True)
    candidate.write_text('{"items": []}')
    git(repo, 'add', '.gitignore')
    assert module().scan(repo, denylist, 'worktree')['status'] == 'ok'
    git(repo, 'add', '-f', 'user-profile/profile/evidence.json')
    result = module().scan(repo, denylist, 'staged')
    assert result['status'] == 'blocked'
    assert {'path': 'user-profile/profile/evidence.json', 'rule_id': 'sensitive.path'} in result['findings']


@pytest.mark.parametrize('relative', ['.codex/hooks.json', '.local/resume-toolkit/project.json', '.claude/settings.local.json', '.claude/hooks/resume-toolkit/runner.py', 'RESUME_TOOLKIT.md'])
def test_local_host_binding_files_are_not_publishable(scan_repo, relative):
    repo, denylist = scan_repo
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{}')
    git(repo, 'add', '-f', relative)
    result = module().scan(repo, denylist, 'staged')
    assert {'path': relative, 'rule_id': 'sensitive.path'} in result['findings']


def test_untracked_visible_files_and_history_filenames_are_scanned(scan_repo):
    repo, denylist = scan_repo
    (repo / 'Secret Fixture Identity.md').write_text('safe')
    result = module().scan(repo, denylist, 'worktree')
    assert result['status'] == 'blocked'
    assert 'Secret Fixture Identity' not in json.dumps(result)
    git(repo, 'add', '.')
    git(repo, 'commit', '-m', 'neutral')
    result = module().scan(repo, denylist, 'history')
    assert result['status'] == 'blocked'
    assert 'Secret Fixture Identity' not in json.dumps(result)


def test_credentials_and_private_ref_names_are_detected_without_printing_value(scan_repo):
    repo, denylist = scan_repo
    secret = 'ghp_' + 'a' * 36
    (repo / 'config.py').write_text('token = ' + repr(secret))
    git(repo, 'add', '.')
    result = module().scan(repo, denylist, 'staged')
    assert {'path': 'config.py', 'rule_id': 'credential.pattern'} in result['findings']
    assert secret not in json.dumps(result)
    (repo / 'config.py').write_text('neutral')
    git(repo, 'add', '.')
    git(repo, 'commit', '-m', 'neutral')
    git(repo, 'branch', 'Secret-Fixture-Identity')
    denylist.write_text(json.dumps({'rules': [{'id': 'private.ref', 'token': 'Secret-Fixture-Identity'}]}))
    assert {'path': '<ref-metadata>', 'rule_id': 'private.ref'} in module().scan(repo, denylist, 'history')['findings']


def test_direct_blob_tags_and_staged_symlinks_fail_closed(scan_repo):
    repo, denylist = scan_repo
    (repo / 'safe.txt').write_text('neutral')
    git(repo, 'add', '.')
    git(repo, 'commit', '-m', 'neutral')
    blob = subprocess.run(['git', '-C', str(repo), 'hash-object', '-w', '--stdin'], input=b'Secret Fixture Identity', capture_output=True, check=True).stdout.decode().strip()
    git(repo, 'tag', 'blob-tag', blob)
    result = module().scan(repo, denylist, 'history')
    assert result['status'] == 'blocked'
    assert any(f['rule_id'] == 'private.fixture' for f in result['findings'])
    safe = subprocess.run(['git', '-C', str(repo), 'hash-object', '-w', '--stdin'], input=b'../outside.txt', capture_output=True, check=True).stdout.decode().strip()
    git(repo, 'update-index', '--add', '--cacheinfo', '120000,' + safe + ',link.txt')
    assert {'path': 'link.txt', 'rule_id': 'unsupported.git-entry'} in module().scan(repo, denylist, 'staged')['findings']


def test_nested_annotated_tag_metadata_and_credential_filename(scan_repo):
    repo, denylist = scan_repo
    (repo / 'safe.txt').write_text('neutral')
    git(repo, 'add', '.')
    git(repo, 'commit', '-m', 'neutral')
    git(repo, 'tag', '-a', 'inner', '-m', 'Secret Fixture Identity')
    git(repo, 'tag', '-a', 'outer', 'inner', '-m', 'neutral')
    git(repo, 'tag', '-d', 'inner')
    assert {'path': '<tag-metadata>', 'rule_id': 'private.fixture'} in module().scan(repo, denylist, 'history')['findings']
    filename = 'ghp_' + 'a' * 36 + '.md'
    (repo / filename).write_text('neutral')
    git(repo, 'add', '.')
    result = module().scan(repo, denylist, 'staged')
    assert result['status'] == 'blocked'
    assert any(f['rule_id'] == 'credential.pattern' for f in result['findings'])
    assert filename not in json.dumps(result)
