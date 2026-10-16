"""Advisory Codex lifecycle routing and byte-freshness checkpoints.

Neither an event nor a user-authored checkpoint authenticates work, reviewer
identity, visual inspection, approval, or permission to continue/submit.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
import uuid

from .onboarding import STATE_TO_SKILL, classify
from .hook_scope import bound_workspace, in_scope
from .records import ToolkitError, _decode, atomic_write_json, confined, load_json, object_fields

SKILLS = ('experience-capture', 'application-materials', 'resume-review', 'cover-letter-review')
PHASES = ('working', 'waiting_for_user', 'blocked', 'paused', 'finished')
EVENTS = ('SessionStart', 'UserPromptSubmit', 'PreCompact', 'Interrupt', 'Stop')
MAX_INPUT = 256_000
MAX_FILES = 64
MAX_FILE_BYTES = 128_000_000
_DIGEST = re.compile(r'[0-9a-f]{64}')
_SESSION = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,255}')
_WARNING = 'Resume Toolkit routing/checkpoint unavailable; run cv onboard and workflow-status with the explicit workspace. No review or completion has been verified.'
_LOG_WARNING = 'Resume Toolkit execution logging unavailable.'


class _ExecutionLog:
    """One atomic record per process; diagnostics do not authenticate origin."""

    def __init__(self, installed_root, probe):
        self.path = None
        self.started = time.monotonic()
        self.data = {}
        try:
            root = _root(installed_root)
            invocation = uuid.uuid4().hex
            relative = f'.codex/resume-toolkit/logs/{invocation}.json'
            path = confined(root, relative, required=False)
            if path != root / relative or path.is_symlink():
                raise ToolkitError('log aliases are unsupported')
            self.data = {
                'schema_version': 1, 'invocation_id': invocation,
                'started_at': datetime.now(timezone.utc).isoformat(),
                'stage': 'started', 'mode': 'manual_probe' if probe else 'hook_command',
                'native_origin_verified': False, 'pid': os.getpid(),
                'workspace_sha256': _digest(os.path.normcase(str(root))),
                'adapter_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'event': None, 'source': None, 'session_sha256': None,
            }
            self.path = path
            self.root = root
            self.relative = relative
            self._write()
        except (OSError, ValueError, RuntimeError):
            self.path = None
            print(_LOG_WARNING, file=sys.stderr)

    def _write(self):
        if self.path is None:
            return
        try:
            if (_root(self.root) != self.root
                    or confined(self.root, self.relative, required=False) != self.path
                    or self.path.is_symlink()):
                raise ToolkitError('log aliases are unsupported')
            self.path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_json(self.path, self.data)
        except (OSError, ValueError, RuntimeError):
            self.path = None
            print(_LOG_WARNING, file=sys.stderr)

    def finish(self, payload, outcome, trace):
        if isinstance(payload, dict):
            event, source, session = (payload.get(key) for key in ('hook_event_name', 'source', 'session_id'))
            self.data['event'] = event if event in EVENTS else None
            self.data['source'] = source if source in ('startup', 'resume', 'clear', 'compact') else None
            if isinstance(session, str) and _SESSION.fullmatch(session):
                self.data['session_sha256'] = _digest(session)
        self.data.update(stage='completed', completed_at=datetime.now(timezone.utc).isoformat(),
                         duration_ms=round((time.monotonic() - self.started) * 1000, 3),
                         outcome=outcome, **trace)
        self._write()


def _digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def _root(workspace):
    root = Path(workspace)
    if not root.is_absolute():
        raise ToolkitError('absolute workspace required')
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ToolkitError('workspace directory required')
    return root


def _state_path(root, session_id):
    if not isinstance(session_id, str) or not _SESSION.fullmatch(session_id):
        raise ToolkitError('invalid session identifier')
    relative = f'.codex/resume-toolkit/sessions/{_digest(session_id)}.json'
    path = confined(root, relative, required=False)
    if path != root / relative or (root / relative).is_symlink():
        raise ToolkitError('checkpoint aliases are unsupported')
    return path


def _file_path(root, relative, *, required=True):
    if not isinstance(relative, str) or len(relative) > 1024:
        raise ToolkitError('invalid snapshot path')
    path = confined(root, relative, required=required)
    # Check the resolved path too: an alias must not snapshot checkpoint state.
    parts = path.relative_to(root).parts
    if not parts or parts[0].lower() in {'.codex', '.git', '.hermes'}:
        raise ToolkitError('cannot snapshot host state')
    return path


def _fingerprint(path):
    if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
        raise ToolkitError('snapshot file unavailable or too large')
    result = hashlib.sha256()
    size = 0
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_FILE_BYTES:
                raise ToolkitError('snapshot file too large')
            result.update(chunk)
    return result.hexdigest()


def _load(root, session_id, path):
    binding = {'schema_version': 1, 'session': _digest(session_id),
               'workspace': _digest(os.path.normcase(str(root)))}
    if not path.exists():
        return dict(binding, route=None, checkpoint=None, last_event=None, interrupted=False)
    state = load_json(path)
    object_fields(state, (*binding, 'route', 'checkpoint', 'last_event', 'interrupted'))
    if type(state['schema_version']) is not int or any(state[key] != value for key, value in binding.items()):
        raise ToolkitError('checkpoint binding mismatch')
    if state['route'] not in (*STATE_TO_SKILL, None) or state['last_event'] not in (*EVENTS, None) or type(state['interrupted']) is not bool:
        raise ToolkitError('invalid routing metadata')
    checkpoint = state['checkpoint']
    if checkpoint is not None:
        object_fields(checkpoint, ('skill', 'phase', 'files'))
        if checkpoint['skill'] not in SKILLS or checkpoint['phase'] not in PHASES:
            raise ToolkitError('invalid workflow declaration')
        snapshots = checkpoint['files']
        if not isinstance(snapshots, list) or len(snapshots) > MAX_FILES:
            raise ToolkitError('invalid snapshot list')
        seen = set()
        for item in snapshots:
            object_fields(item, ('path', 'sha256'))
            _file_path(root, item['path'], required=False)
            if item['path'] in seen or not isinstance(item['sha256'], str) or not _DIGEST.fullmatch(item['sha256']):
                raise ToolkitError('invalid snapshot fingerprint')
            seen.add(item['path'])
    return state


@contextmanager
def _locked(path):
    """Fail visibly on contention/crashed writers; never discard another lock."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_suffix('.lock')
    # A dangling symlink must also be treated as an existing lock.
    try:
        stream = lock.open('xb')
    except OSError:
        raise ToolkitError('checkpoint busy; inspect session lock') from None
    try:
        stream.close()
        yield
    finally:
        lock.unlink()


def record_checkpoint(workspace, session_id, skill, phase, paths):
    """Record a declaration and optional file snapshot, never an approval."""
    root = _root(workspace)
    path = _state_path(root, session_id)
    if skill not in SKILLS or phase not in PHASES:
        raise ToolkitError('invalid workflow declaration')
    if not isinstance(paths, (list, tuple)) or len(paths) > MAX_FILES:
        raise ToolkitError('invalid snapshot list')
    snapshots = []
    for relative in paths:
        file = _file_path(root, relative)
        normalized = relative.replace('\\', '/')
        if any(item['path'] == normalized for item in snapshots):
            raise ToolkitError('duplicate snapshot file')
        snapshots.append({'path': normalized, 'sha256': _fingerprint(file)})
    with _locked(path):
        state = _load(root, session_id, path)
        state['checkpoint'] = {'skill': skill, 'phase': phase, 'files': snapshots}
        atomic_write_json(path, state)
    return checkpoint_status(root, session_id)


def checkpoint_status(workspace, session_id):
    """Recompute byte freshness for the selected files; no semantic guarantees."""
    root = _root(workspace)
    state = _load(root, session_id, _state_path(root, session_id))
    snapshots = (state['checkpoint'] or {}).get('files', [])
    changed = []
    for item in snapshots:
        try:
            current = _fingerprint(_file_path(root, item['path']))
        except (ValueError, OSError, RuntimeError):
            current = None
        if current != item['sha256']:
            changed.append(item['path'])
    return {key: state[key] for key in ('route', 'checkpoint', 'last_event', 'interrupted')} | {
        'freshness': 'stale' if changed else ('fresh' if snapshots else 'not_recorded'),
        'changed_files': changed, 'review_status': 'unreviewed_preview',
        'release_available': False,
    }


def _context(route, state, session, workspace, project):
    text = ('Resume Toolkit advisory context. Apply only to the requested candidate/application work; '
            'do not redirect unrelated requests. Reconcile this context with current user instructions. '
            f'Current hook session ID for cv workflow-checkpoint/workflow-status: {session}. '
            f'Use explicit data workspace {workspace} for cv commands and canonical records. '
            f'Load skills and references from {project / ".agents/skills"}. '
            + route.as_context()['context'])
    checkpoint = state['checkpoint']
    if checkpoint:
        text += (f" Saved workflow declaration: {checkpoint['skill']}; phase {checkpoint['phase']}. "
                 f"Selected-file freshness: {state['freshness']}. "
                 'Read canonical records and prior answers before continuing; never ask again for an answer already persisted. '
                 'Waiting, blocked, paused or finished declarations do not authorize automatic continuation. ')
        if route.state == 'ready':
            text += (f"For an authorized continuation, load the saved {checkpoint['skill']} skill instead of restarting application intake. "
                     'A changed user request takes precedence over the saved workflow. ')
    if state['interrupted']:
        text += 'The session was interrupted; respect the interruption and await explicit user direction. '
    text += ('For review, use actual independent agents and visual tools on the exact rendered artifacts; '
             'report missing capabilities. Recheck all selected inputs and outputs with cv workflow-status before final claims/export. '
             'A declaration or fresh hash does not prove independent review, visual inspection, completeness, or approval. '
             'All artifacts remain previews; no guarded release exists.')
    return text


def dispatch(payload, workspace, *, project_root=None, _trace=None):
    """Consume documented host metadata only; never read transcripts or messages."""
    trace = _trace if _trace is not None else {}
    trace['outcome'] = 'ignored'
    if not isinstance(payload, dict) or payload.get('hook_event_name') not in EVENTS:
        return {}
    session = payload.get('session_id')
    if not in_scope(payload, workspace, project_root):
        return {}
    try:
        root = _root(workspace)
        project = _root(project_root or root)
    except (OSError, ValueError, RuntimeError):
        return {}
    try:
        event = payload['hook_event_name']
        path = _state_path(root, session)
        route = classify(root) if event in ('SessionStart', 'UserPromptSubmit') else None
        with _locked(path):
            state = _load(root, session, path)
            if route is not None:
                state['route'] = route.state
            if event == 'Interrupt':
                state['interrupted'] = True
            elif event == 'UserPromptSubmit':
                # New user direction, not a hook-generated continuation: we
                # never emit Stop block decisions that create such prompts.
                state['interrupted'] = False
            state['last_event'] = event
            atomic_write_json(path, state)
        if route is not None:
            status = checkpoint_status(root, session)
            trace.update(outcome='context_emitted', route=route.state, freshness=status['freshness'])
            return {'hookSpecificOutput': {'hookEventName': event,
                    'additionalContext': _context(route, status, session, root, project)}}
        trace.update(outcome='observed', route=state['route'])
        return {}
    except (OSError, ValueError, RuntimeError, RecursionError, OverflowError, TypeError):
        trace['outcome'] = 'error'
        return {'systemMessage': _WARNING}


def main(installed_root, workspace_relative='.'):
    """Installed runner entrypoint, independent of cwd/PYTHONPATH/package install."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True, type=Path)
    parser.add_argument('--probe', action='store_true', help='Label this invocation as a manual diagnostic probe')
    args = parser.parse_args()
    # Keep diagnostics and checkpoints with private data, not project sources.
    try:
        data_root = bound_workspace(installed_root, workspace_relative)
    except (OSError, ValueError, RuntimeError):
        print(json.dumps({'systemMessage': _WARNING}, sort_keys=True))
        return 0
    log = _ExecutionLog(data_root, args.probe)
    payload, trace, outcome = None, {}, 'invalid_input'
    try:
        if _root(args.workspace) != data_root:
            outcome = 'workspace_mismatch'
            raise ToolkitError('installation workspace mismatch')
        raw = sys.stdin.buffer.read(MAX_INPUT + 1)
        if len(raw) > MAX_INPUT:
            raise ToolkitError('hook input too large')
        payload = _decode(raw)
        result = dispatch(payload, data_root, project_root=installed_root, _trace=trace)
        outcome = trace.pop('outcome')
    except (OSError, ValueError, RuntimeError, RecursionError, OverflowError):
        result = {'systemMessage': _WARNING}
    print(json.dumps(result, sort_keys=True))
    log.finish(payload, outcome, trace)
    return 0
