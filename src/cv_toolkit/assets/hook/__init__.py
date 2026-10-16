"""Opt-in project entry routing; advisory context, not a drafting sandbox.

The current Hermes pre_llm_call payload has no workspace field. This adapter
therefore supports a dedicated CLI process launched at the opted-in project
root. It stays silent if process cwd differs; shared desktop/gateway processes
are not certified by this integration. No cached system prompt is modified.
"""
from pathlib import Path
import json

from . import onboarding
from .cv_toolkit.hook_scope import bound_workspace


def _project_root():
    return Path(__file__).resolve().parents[3]


def _route(**kwargs):
    project = _project_root()
    if Path.cwd().resolve() != project:
        return None
    # An absent platform is not evidence of a dedicated CLI session.
    if kwargs.get('platform') != 'cli':
        return None
    try:
        binding = json.loads((Path(__file__).parent / 'binding.json').read_text(encoding='utf-8'))
        root = bound_workspace(project, binding['workspace'])
        state = onboarding.classify(root)
        context = state.as_context()['context']
    except Exception:
        # Do not expose record contents/paths or silently imply readiness.
        context = ('Workspace routing could not be validated. Stop application '
                   'drafting and diagnose the workspace using the toolkit CLI. '
                   'Do not infer candidate facts or overwrite evidence.')
        return {'context': context}
    return {'context': (
        'Resume Toolkit entry routing (advisory; not evidence approval). '
        'For application work, follow this route; respect an explicit user stop '
        'or unrelated request. Recheck records after changes before drafting. '
        + context
        + f' Use the explicit data workspace {root} for every cv command and canonical record. '
        + f' Load the named skill from {project / ".hermes/skills"} '
        'and read its references; if skill discovery is unavailable, read the '
        'SKILL.md by absolute path. Never use another person\'s host memory as '
        'candidate evidence. Structural validity does not prove factual truth.'
    )}


def register(ctx):
    ctx.register_hook('pre_llm_call', _route)
