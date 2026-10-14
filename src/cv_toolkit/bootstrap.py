"""Explicit empty-workspace creation and packaged host-skill installation."""
from importlib.resources import files
import json
from pathlib import Path
import shlex
import sys

from .records import ToolkitError, confined, nonempty


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
    (root / '.gitignore').write_text('outputs/\n.env\n.env.*\nprivate/\n.hermes/\n.codex/\n', encoding='utf-8')
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


HOOK_NAME = 'resume-toolkit'

# cv_toolkit dependency modules the classifier imports.   Bundled verbatim next
# to onboarding.py so the installed Hermes plugin is self-contained and can
# reuse the canonical validators whether or not cv_toolkit is also installed.
_HOOK_DEPENDENCIES = ('__init__.py', 'records.py', 'evidence.py', 'projection.py', 'workspace.py')


def _hook_resources():
    """Return the Hermes project-plugin payload for the entry workflow hook.

    ``onboarding.py`` is copied verbatim from ``cv_toolkit.onboarding`` so the
    installed plugin can never drift from the canonical module. The manifest and
    ``__init__.py`` are static assets. Because the classifier reuses the
    canonical validators, the needed ``cv_toolkit`` dependency modules are
    bundled alongside it (``cv_toolkit/*.py``); an explicitly installed
    ``cv_toolkit`` package is an equivalent supported alternative.
    """
    hook_dir = files('cv_toolkit').joinpath('assets', 'hook')
    yield 'plugin.yaml', hook_dir.joinpath('plugin.yaml').read_bytes()
    manifest = hook_dir.joinpath('__init__.py').read_bytes()
    yield '__init__.py', manifest
    yield 'onboarding.py', files('cv_toolkit').joinpath('onboarding.py').read_bytes()
    for module in _HOOK_DEPENDENCIES:
        source = files('cv_toolkit').joinpath(module)
        if source.is_file():
            yield f'cv_toolkit/{module}', source.read_bytes()


def install_entry_hook(root, host):
    """Install a state-aware host adapter into a private workspace.

    Refuses to overwrite an existing installation. Writes
    ``<root>/.hermes/plugins/resume-toolkit/{plugin.yaml,__init__.py,onboarding.py}``.
    The hook only loads when Hermes is launched from ``root`` with project
    plugins enabled and ``resume-toolkit`` under ``plugins.enabled``.
    """
    if host == 'codex':
        return _install_codex_hook(root)
    prefix = {'hermes': '.hermes/plugins'}.get(host)
    if prefix is None:
        raise ToolkitError('invalid hook host')
    root = Path(root).resolve(strict=True)
    target = root / prefix / HOOK_NAME
    if target.exists() or target.is_symlink():
        raise ToolkitError('hook already installed')
    if not target.resolve(strict=False).is_relative_to(root):
        raise ToolkitError('hook path escapes workspace')
    payload = list(_hook_resources())
    for relative, raw in payload:
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return len(payload)


def _install_codex_hook(root):
    """Write a standalone native hook bundle; never merge config or grant trust."""
    from .codex_hooks import EVENTS

    root = Path(root).resolve(strict=True)
    config = confined(root, '.codex/hooks.json', required=False)
    target = confined(root, '.codex/hooks/resume-toolkit', required=False)
    if (config != root / '.codex/hooks.json' or target != root / '.codex/hooks/resume-toolkit'
            or (root / '.codex/hooks.json').is_symlink()
            or (root / '.codex/hooks/resume-toolkit').is_symlink()):
        raise ToolkitError('Codex installation aliases are unsupported')
    if config.exists() or config.is_symlink() or target.exists() or target.is_symlink():
        raise ToolkitError('Codex hook config or bundle already exists; inspect before installing')
    runner = (
        'from pathlib import Path\n'
        'import sys\n'
        'folder = Path(__file__).resolve().parent\n'
        'sys.path.insert(0, str(folder))\n'
        'from cv_toolkit.codex_hooks import main\n'
        'raise SystemExit(main(folder.parents[2]))\n'
    )
    payload = [('run.py', runner.encode('utf-8'))]
    for module in (*_HOOK_DEPENDENCIES, 'onboarding.py', 'codex_hooks.py'):
        payload.append((f'cv_toolkit/{module}', files('cv_toolkit').joinpath(module).read_bytes()))
    argv = [str(Path(sys.executable).resolve()), '-I', str(target / 'run.py'), '--workspace', str(root)]
    windows = '& ' + ' '.join("'" + arg.replace("'", "''") + "'" for arg in argv)
    command = shlex.join(argv)
    hooks = {event: [{'hooks': [{'type': 'command', 'command': command,
              'commandWindows': windows, 'timeout': 3 if event == 'Interrupt' else 10}]}]
             for event in EVENTS}
    # Complete all resource reads/path checks before writing any installation.
    destinations = [(confined(root, (target / relative).relative_to(root).as_posix(), required=False), raw)
                    for relative, raw in payload]
    for path, raw in destinations:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
    with config.open('x', encoding='utf-8') as stream:
        json.dump({'hooks': hooks}, stream, indent=2)
        stream.write('\n')
    return len(payload) + 1
