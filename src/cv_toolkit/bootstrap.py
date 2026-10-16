"""Explicit empty-workspace creation and packaged host-skill installation."""
from importlib.resources import files
import json
from pathlib import Path
import shlex
import sys

from .records import ToolkitError, atomic_write_json, confined, load_json, nonempty, object_fields, schema


SKILLS = ('experience-capture', 'application-materials', 'resume-review', 'cover-letter-review')
EXAMPLES = ('developer', 'researcher', 'showcase')


def init_workspace(root, *, name='Candidate', example=None):
    root = Path(root)
    nonempty(name, 'candidate name')
    if example is not None and example not in EXAMPLES:
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


class WorkspaceBindingError(ToolkitError):
    """An explicit project/data binding cannot safely be used."""


def workspace_project_root(root, project_root=None):
    """Resolve an explicit discovery root without inferring a candidate path."""
    workspace = Path(root).expanduser().resolve()
    if project_root is None:
        return workspace
    try:
        project = Path(project_root).expanduser().resolve(strict=True)
        if not project.is_dir() or not workspace.is_relative_to(project):
            raise WorkspaceBindingError('Workspace must be inside the explicit project root.')
        for parent in (project / '.local', project / '.local/resume-toolkit'):
            if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
                raise WorkspaceBindingError(
                    'Project workspace binding directory is obstructed or aliased; '
                    'inspect .local/resume-toolkit before retrying; nothing was changed.')
        binding = confined(project, '.local/resume-toolkit/project.json', required=False)
        if binding != project / '.local/resume-toolkit/project.json' or binding.is_symlink():
            raise WorkspaceBindingError('Project workspace binding aliases are unsupported.')
        if binding.exists():
            record = load_json(binding)
            object_fields(record, {'schema_version', 'workspace'}, rule='project workspace binding')
            schema(record['schema_version'])
            bound = confined(project, record['workspace'], required=False)
            if bound != project / record['workspace']:
                raise WorkspaceBindingError(
                    'Project workspace binding aliases are unsupported; inspect the pinned '
                    'data path before retrying; nothing was changed.')
            if bound != workspace:
                raise WorkspaceBindingError(
                    'Project workspace binding conflicts. Inspect .local/resume-toolkit/project.json '
                    'and existing host instructions before deliberately rebinding; nothing was changed.')
        return project
    except WorkspaceBindingError:
        raise
    except (OSError, ValueError, RuntimeError):
        raise WorkspaceBindingError(
            'Invalid project workspace binding. Use an existing project directory and inspect '
            '.local/resume-toolkit/project.json before retrying; nothing was changed.') from None


def install_skills(root, host, project_root=None):
    prefix = {'codex': '.agents/skills', 'claude': '.claude/skills', 'hermes': '.hermes/skills'}.get(host)
    if prefix is None:
        raise ToolkitError('invalid skill host')
    Path(root).resolve(strict=True)
    root = workspace_project_root(root, project_root)
    payload = []
    for name in SKILLS:
        folder = root / prefix / name
        if folder.exists() or folder.is_symlink():
            raise ToolkitError('skill already exists')
        if folder.resolve(strict=False) != folder:
            raise ToolkitError('skill installation aliases are unsupported')
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
_HOOK_DEPENDENCIES = ('__init__.py', 'records.py', 'evidence.py', 'projection.py', 'workspace.py', 'hook_scope.py')


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


def install_entry_hook(root, host, *, project_root=None):
    """Install advisory hooks at an explicit project, pinned to its data root.

    Same-root installation remains the default. Existing toolkit bundles are
    never overwritten. Claude preserves unrelated local settings and hooks;
    Codex refuses an existing hook config. Hermes requires separate opt-ins.
    No global configuration, project trust or hook trust is changed.
    """
    project = workspace_project_root(root, project_root)
    root = Path(root).resolve(strict=True)
    if host == 'codex':
        return _install_codex_hook(root, project)
    if host == 'claude':
        return _install_claude_hook(root, project)
    prefix = {'hermes': '.hermes/plugins'}.get(host)
    if prefix is None:
        raise ToolkitError('invalid hook host')
    target = project / prefix / HOOK_NAME
    if target.exists() or target.is_symlink():
        raise ToolkitError('hook already installed')
    if target.resolve(strict=False) != target:
        raise ToolkitError('hook installation aliases are unsupported')
    payload = list(_hook_resources())
    payload.append(('binding.json', (json.dumps({'workspace': root.relative_to(project).as_posix()}) + '\n').encode()))
    for relative, raw in payload:
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    return len(payload)


def _install_codex_hook(root, project=None):
    """Write a standalone native hook bundle; never merge config or grant trust."""
    from .codex_hooks import EVENTS

    root = Path(root).resolve(strict=True)
    project = project or root
    config = confined(project, '.codex/hooks.json', required=False)
    target = confined(project, '.codex/hooks/resume-toolkit', required=False)
    if (config != project / '.codex/hooks.json' or target != project / '.codex/hooks/resume-toolkit'
            or (project / '.codex/hooks.json').is_symlink()
            or (project / '.codex/hooks/resume-toolkit').is_symlink()):
        raise ToolkitError('Codex installation aliases are unsupported')
    if config.exists() or config.is_symlink() or target.exists() or target.is_symlink():
        raise ToolkitError('Codex hook config or bundle already exists; inspect before installing')
    runner = (
        'from pathlib import Path\n'
        'import sys\n'
        'folder = Path(__file__).resolve().parent\n'
        'sys.path.insert(0, str(folder))\n'
        'from cv_toolkit.codex_hooks import main\n'
        f'raise SystemExit(main(folder.parents[2], {root.relative_to(project).as_posix()!r}))\n'
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
    destinations = [(confined(project, (target / relative).relative_to(project).as_posix(), required=False), raw)
                    for relative, raw in payload]
    for path, raw in destinations:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
    with config.open('x', encoding='utf-8') as stream:
        json.dump({'hooks': hooks}, stream, indent=2)
        stream.write('\n')
    return len(payload) + 1


def _install_claude_hook(root, project):
    """Merge additive local entry hooks, preserving all existing owner settings."""
    from .claude_hooks import EVENTS

    config = confined(project, '.claude/settings.local.json', required=False)
    target = confined(project, '.claude/hooks/resume-toolkit', required=False)
    if (config != project / '.claude/settings.local.json'
            or target != project / '.claude/hooks/resume-toolkit'
            or config.is_symlink() or target.is_symlink()):
        raise ToolkitError('Claude installation aliases are unsupported')
    if target.exists():
        raise ToolkitError('Claude hook bundle already exists; inspect before installing')
    settings = load_json(config) if config.exists() else {}
    if not isinstance(settings, dict) or not isinstance(settings.get('hooks', {}), dict):
        raise ToolkitError('invalid existing Claude hook settings')
    hooks = settings.setdefault('hooks', {})
    if any(not isinstance(groups, list) for groups in hooks.values()):
        raise ToolkitError('invalid existing Claude hook groups')
    if 'resume-toolkit' in json.dumps(hooks):
        raise ToolkitError('Claude toolkit hook definition already exists; inspect before installing')
    runner = (
        'from pathlib import Path\n'
        'import sys\n'
        'folder = Path(__file__).resolve().parent\n'
        'sys.path.insert(0, str(folder))\n'
        'from cv_toolkit.claude_hooks import main\n'
        f'raise SystemExit(main(folder.parents[2], {root.relative_to(project).as_posix()!r}))\n'
    )
    payload = [('run.py', runner.encode('utf-8'))]
    for module in (*_HOOK_DEPENDENCIES, 'onboarding.py', 'claude_hooks.py'):
        payload.append((f'cv_toolkit/{module}', files('cv_toolkit').joinpath(module).read_bytes()))
    # Claude's documented exec form avoids shell interpretation on all platforms.
    handler = {'type': 'command', 'command': str(Path(sys.executable).resolve()),
               'args': ['-I', str(target / 'run.py'), '--workspace', str(root)], 'timeout': 10}
    for event in EVENTS:
        hooks.setdefault(event, []).append({'hooks': [dict(handler)]})
    destinations = [(confined(project, (target / relative).relative_to(project).as_posix(), required=False), raw)
                    for relative, raw in payload]
    for path, raw in destinations:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
    atomic_write_json(config, settings)
    return len(payload) + 1
