"""Advisory Codex lifecycle routing and byte-freshness checkpoints.

Neither an event nor a user-authored checkpoint authenticates work, reviewer
identity, visual inspection, approval, or permission to continue/submit.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from .onboarding import STATE_TO_SKILL, classify
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


def _context(route, state, session):
    text = ('Resume Toolkit advisory context. Apply only to the requested candidate/application work; '
            'do not redirect unrelated requests. Reconcile this context with current user instructions. '
            f'Current hook session ID for cv workflow-checkpoint/workflow-status: {session}. '
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


def dispatch(payload, workspace):
    """Consume documented host metadata only; never read transcripts or messages."""
    if not isinstance(payload, dict) or payload.get('hook_event_name') not in EVENTS:
        return {}
    session = payload.get('session_id')
    cwd = payload.get('cwd')
    if not isinstance(session, str) or not _SESSION.fullmatch(session) or not isinstance(cwd, str) or not Path(cwd).is_absolute():
        return {}
    try:
        root = _root(workspace)
        session_cwd = Path(cwd).resolve(strict=True)
        if not session_cwd.is_relative_to(root):
            return {}
        current = session_cwd
        while current != root:
            if (current / 'cvtool.toml').exists():
                return {}  # Inherited outer hooks cannot bind a nested workspace.
            current = current.parent
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
            return {'hookSpecificOutput': {'hookEventName': event,
                    'additionalContext': _context(route, checkpoint_status(root, session), session)}}
        return {}
    except (OSError, ValueError, RuntimeError, RecursionError, OverflowError, TypeError):
        return {'systemMessage': _WARNING}


def main(installed_root):
    """Installed runner entrypoint, independent of cwd/PYTHONPATH/package install."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True, type=Path)
    args = parser.parse_args()
    try:
        if _root(args.workspace) != _root(installed_root):
            raise ToolkitError('installation workspace mismatch')
        raw = sys.stdin.buffer.read(MAX_INPUT + 1)
        if len(raw) > MAX_INPUT:
            raise ToolkitError('hook input too large')
        result = dispatch(_decode(raw), args.workspace)
    except (OSError, ValueError, RuntimeError, RecursionError, OverflowError):
        result = {'systemMessage': _WARNING}
    print(json.dumps(result, sort_keys=True))
    return 0
