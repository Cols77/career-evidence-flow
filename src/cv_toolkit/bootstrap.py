"""Explicit empty-workspace creation and packaged host-skill installation."""
from importlib.resources import files
import json
from pathlib import Path

from .records import ToolkitError, nonempty


SKILLS = ('experience-capture', 'application-materials', 'resume-review', 'cover-letter-review')


def init_workspace(root, *, name='Candidate', example=None):
    root = Path(root)
    nonempty(name, 'candidate name')
    if example not in {None, 'developer', 'researcher'}:
        raise ToolkitError('invalid example')
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise ToolkitError('workspace must be empty')
    payload = {}
    if example:
        folder = files('cv_toolkit').joinpath('assets', 'examples', example)
        for source in folder.iterdir():
            if source.is_file():
                target = 'profile/' + source.name if source.name.endswith('.json') else source.name
                payload[target] = source.read_bytes()
    else:
        config = '[profile]\ndisplay_name = ' + json.dumps(name, ensure_ascii=False) + '\n\n[paths]\nprofile = "profile"\napplications = "applications"\nstyles = "styles"\noutputs = "outputs"\n'
        payload = {'cvtool.toml': config.encode('utf-8'), 'profile/evidence.json': (json.dumps({'schema_version': '1', 'candidate_id': 'candidate.new', 'items': []}, indent=2) + '\n').encode(), 'profile/registry.json': b'[]\n'}
    root.mkdir(parents=True, exist_ok=True)
    for relative, raw in payload.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    for name in ('applications', 'styles', 'outputs'):
        (root / name).mkdir(exist_ok=True)
    (root / '.gitignore').write_text('outputs/\n.env\n.env.*\nprivate/\n.hermes/\n', encoding='utf-8')
    return root


def install_skills(root, host):
    prefix = {'codex': '.agents/skills', 'claude': '.claude/skills', 'hermes': '.hermes/skills'}.get(host)
    if prefix is None:
        raise ToolkitError('invalid skill host')
    root = Path(root).resolve(strict=True)
    payload = []
    for name in SKILLS:
        folder = root / prefix / name
        if folder.exists() or folder.is_symlink():
            raise ToolkitError('skill already exists')
        if not folder.resolve(strict=False).is_relative_to(root):
            raise ToolkitError('skill path escapes workspace')
        source = files('cv_toolkit').joinpath('assets', 'skills', name)
        if not source.joinpath('SKILL.md').is_file():
            raise ToolkitError('skill manifest missing')
        payload.extend(_skill_resources(source, folder))
    for target, raw in payload:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    return len(SKILLS)


def _skill_resources(source, target):
    """Copy Traversable resources, including references, outside the source tree."""
    for resource in source.iterdir():
        destination = target / resource.name
        if resource.is_dir():
            yield from _skill_resources(resource, destination)
        elif resource.is_file():
            yield destination, resource.read_bytes()
