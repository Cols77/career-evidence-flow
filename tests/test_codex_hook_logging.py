"""Installed-runner diagnostics with synthetic data; no native delivery claims."""
import hashlib
import json
import subprocess
import sys
import time

import pytest

from cv_toolkit.bootstrap import init_workspace, install_entry_hook
from cv_toolkit import codex_hooks as hooks


@pytest.fixture
def installed(tmp_path):
    root = init_workspace(tmp_path / 'private workspace')
    install_entry_hook(root, 'codex')
    return root


def run(root, payload, *extra):
    script = root / '.codex/hooks/resume-toolkit/run.py'
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run([sys.executable, '-I', str(script), '--workspace', str(root), *extra],
                          input=raw, capture_output=True, text=True, timeout=30)


def records(root):
    return [json.loads(p.read_text(encoding='utf-8'))
            for p in (root / '.codex/resume-toolkit/logs').glob('*.json')]


@pytest.mark.parametrize('event', hooks.EVENTS)
def test_installed_execution_logs_outcome_without_private_content(installed, event):
    result = run(installed, {'hook_event_name': event, 'session_id': 'private-session',
                            'cwd': str(installed), 'source': 'compact',
                            'prompt': 'PRIVATE PROMPT', 'last_assistant_message': 'PRIVATE RESUME',
                            'transcript_path': 'PRIVATE PATH'})
    assert result.returncode == 0 and result.stderr == ''
    assert isinstance(json.loads(result.stdout), dict)
    entries = records(installed)
    assert len(entries) == 1
    entry = entries[0]
    assert entry['stage'] == 'completed' and entry['event'] == event
    assert entry['outcome'] == ('context_emitted' if event in ('SessionStart', 'UserPromptSubmit') else 'observed')
    assert entry['mode'] == 'hook_command' and entry['native_origin_verified'] is False
    assert entry['session_sha256'] == hashlib.sha256(b'private-session').hexdigest()
    assert entry['duration_ms'] >= 0 and entry['started_at'] <= entry['completed_at']
    assert len(entry['adapter_sha256']) == 64
    assert entry['pid'] > 0
    stored = json.dumps(entry)
    assert all(value not in stored for value in ('private-session', str(installed), 'PRIVATE PROMPT', 'PRIVATE RESUME', 'PRIVATE PATH'))


def test_probe_is_explicit_and_invocations_do_not_overwrite(installed):
    data = {'hook_event_name': 'Stop', 'session_id': 's', 'cwd': str(installed)}
    for _ in range(2):
        assert run(installed, data, '--probe').returncode == 0
    entries = records(installed)
    assert len(entries) == 2 and len({e['invocation_id'] for e in entries}) == 2
    assert all(e['mode'] == 'manual_probe' for e in entries)


@pytest.mark.parametrize('raw', ['{broken PRIVATE', '[]', 'null', 'x' * (hooks.MAX_INPUT + 1)],
                         ids=['malformed', 'array', 'null', 'oversized'])
def test_rejected_input_is_logged_without_echoing_it(installed, raw):
    result = run(installed, raw)
    entry, = records(installed)
    assert result.returncode == 0
    assert entry['stage'] == 'completed'
    assert entry['outcome'] in ('invalid_input', 'ignored')
    assert entry['event'] is None and entry['session_sha256'] is None
    assert 'PRIVATE' not in json.dumps(entry)


def test_corrupt_state_logs_failure_but_not_exception_detail(installed):
    hooks.record_checkpoint(installed, 's', 'resume-review', 'working', [])
    path = next((installed / '.codex/resume-toolkit/sessions').glob('*.json'))
    path.write_text('{PRIVATE CORRUPTION', encoding='utf-8')
    result = run(installed, {'hook_event_name': 'Stop', 'session_id': 's', 'cwd': str(installed)})
    assert 'systemMessage' in json.loads(result.stdout)
    entry, = records(installed)
    assert entry['outcome'] == 'error'
    assert 'PRIVATE CORRUPTION' not in json.dumps(entry)


def test_foreign_scope_is_logged_as_ignored(installed, tmp_path):
    result = run(installed, {'hook_event_name': 'SessionStart', 'session_id': 's', 'cwd': str(tmp_path)})
    assert json.loads(result.stdout) == {}
    entry, = records(installed)
    assert entry['outcome'] == 'ignored'


def test_logging_failure_does_not_break_routing(installed):
    logs = installed / '.codex/resume-toolkit/logs'
    logs.parent.mkdir(parents=True)
    logs.write_text('PRIVATE user file', encoding='utf-8')
    result = run(installed, {'hook_event_name': 'SessionStart', 'session_id': 's', 'cwd': str(installed)})
    assert 'hookSpecificOutput' in json.loads(result.stdout)
    assert result.returncode == 0 and 'execution logging unavailable' in result.stderr
    assert 'PRIVATE' not in result.stderr and str(installed) not in result.stderr
    assert logs.read_text(encoding='utf-8') == 'PRIVATE user file'


def test_killed_process_leaves_started_record(installed):
    script = installed / '.codex/hooks/resume-toolkit/run.py'
    proc = subprocess.Popen([sys.executable, '-I', str(script), '--workspace', str(installed), '--probe'],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        deadline = time.monotonic() + 10
        while not records(installed) and time.monotonic() < deadline:
            time.sleep(.02)
        entry, = records(installed)
        assert entry['stage'] == 'started' and entry['pid'] == proc.pid
        assert 'completed_at' not in entry
    finally:
        proc.terminate()
        proc.communicate(timeout=10)
    assert records(installed)[0]['stage'] == 'started'


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows junction confinement')
def test_log_directory_alias_cannot_redirect_writes(installed, tmp_path):
    logs = installed / '.codex/resume-toolkit/logs'
    logs.parent.mkdir(parents=True)
    target = tmp_path / 'outside logs'
    target.mkdir()
    created = subprocess.run(['cmd', '/c', 'mklink', '/J', str(logs), str(target)], capture_output=True)
    assert created.returncode == 0
    try:
        result = run(installed, {'hook_event_name': 'Stop', 'session_id': 's', 'cwd': str(installed)})
        assert result.returncode == 0 and 'execution logging unavailable' in result.stderr
        assert not list(target.iterdir())
    finally:
        logs.rmdir()  # Remove the junction itself; never traverse its target.


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows junction confinement')
def test_log_directory_swapped_after_start_cannot_redirect_completion(installed, tmp_path, capsys):
    log = hooks._ExecutionLog(installed, True)
    logs = installed / '.codex/resume-toolkit/logs'
    saved = logs.with_name('original-logs')
    logs.rename(saved)
    outside = tmp_path / 'outside after start'
    outside.mkdir()
    created = subprocess.run(['cmd', '/c', 'mklink', '/J', str(logs), str(outside)], capture_output=True)
    assert created.returncode == 0
    try:
        log.finish({}, 'ignored', {})
        assert not list(outside.iterdir())
        assert 'execution logging unavailable' in capsys.readouterr().err
        original, = saved.glob('*.json')
        assert json.loads(original.read_text())['stage'] == 'started'
    finally:
        logs.rmdir()
