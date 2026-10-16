"""Claude entry routing; advisory context, never approval or continuation."""
import argparse
import json
from pathlib import Path
import sys

from .hook_scope import bound_workspace, in_scope
from .onboarding import classify
from .records import ToolkitError, _decode

EVENTS = ('SessionStart', 'UserPromptSubmit')
MAX_INPUT = 256_000
WARNING = 'Resume Toolkit routing unavailable; run cv onboard with the explicit workspace. No review or completion has been verified.'


def dispatch(payload, workspace, project_root=None):
    if (not isinstance(payload, dict) or payload.get('hook_event_name') not in EVENTS
            or not in_scope(payload, workspace, project_root)):
        return {}
    try:
        root = Path(workspace).resolve(strict=True)
        project = Path(project_root or root).resolve(strict=True)
        route = classify(root)
        context = (
            'Resume Toolkit advisory entry routing. Apply only to requested candidate/application work; '
            'respect an explicit stop or unrelated request. '
            f'Use the explicit data workspace {root} for every cv command and canonical record. '
            f'Load workflow skills and references from {project / ".claude/skills"}. '
            + route.as_context()['context']
            + ' Save actual supplied answers with provenance before use; never infer facts from host memory. '
            'Use actual independent reviewers and visual tools on exact artifacts; report missing capabilities. '
            'This hook does not save answers or restore task checkpoints. Reconcile canonical records after compaction. '
            'All documents remain previews; no review, completion, or submission has been approved.'
        )
        return {'hookSpecificOutput': {'hookEventName': payload['hook_event_name'],
                                       'additionalContext': context}}
    except (OSError, ValueError, RuntimeError, TypeError, RecursionError):
        return {'systemMessage': WARNING}


def main(installed_project, workspace_relative='.'):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', required=True, type=Path)
    args = parser.parse_args()
    try:
        root = bound_workspace(installed_project, workspace_relative)
        if args.workspace.resolve(strict=True) != root:
            raise ToolkitError('installation workspace mismatch')
        raw = sys.stdin.buffer.read(MAX_INPUT + 1)
        if len(raw) > MAX_INPUT:
            raise ToolkitError('hook input too large')
        result = dispatch(_decode(raw), root, installed_project)
    except (OSError, ValueError, RuntimeError, RecursionError, OverflowError):
        result = {'systemMessage': WARNING}
    print(json.dumps(result, sort_keys=True))
    return 0
