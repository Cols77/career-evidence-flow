"""Workspace-local installation and read-only deployment diagnostics.

Installed files do not prove host discovery, hook execution or review quality.
"""
from importlib.resources import files
from pathlib import Path
import shutil
import subprocess

from .bootstrap import SKILLS, _skill_resources, init_workspace
from .evidence import _require_source_registry, build_source_registry, load_evidence
from .onboarding import classify
from .projection import load_projection
from .records import ToolkitError, load_json
from .workspace import Workspace


HOSTS = {'codex': '.agents/skills', 'claude': '.claude/skills', 'hermes': '.hermes/skills'}


class DeploymentError(ToolkitError):
    """Actionable installation failure without candidate record contents."""


_GUIDE = '''# Resume Toolkit workspace

Start the chosen host from this private workspace with the Python environment
containing `cv` activated. Run `cv doctor --workspace . --host HOST` (codex,
claude, hermes or all), then `cv onboard --workspace .`. Follow the returned
workflow and read its SKILL.md and linked references before drafting.

Installed project skills are in `.agents/skills/` for Codex,
`.claude/skills/` for Claude Code, and `.hermes/skills/` for Hermes. Only the
hosts selected during setup have these copies. If native discovery is
unavailable, ask the agent to read the selected directory's
`experience-capture/SKILL.md` or `application-materials/SKILL.md` explicitly.
Codex uses `$experience-capture` / `$application-materials`; Claude Code and
Hermes use `/experience-capture` / `/application-materials` after discovery.

For example: "Use this explicit private workspace. Read RESUME_TOOLKIT.md,
run cv onboard with this workspace path, load the returned skill and its
references, and help me capture my experience or prepare application previews."

An empty profile needs an experience interview/import. Synthetic examples are
demonstrations, never evidence about the user. Save actual answers with
provenance before using them. Keep personal records in this private workspace.
Read employer deliverable and AI-use instructions before drafting. Write all
generated documents and reviews under the configured outputs directory and
verify its Git ignore rules. Use separate applications for separate jobs.

Use actual separate agents for the independent resume-review and, when needed,
cover-letter-review workflows; report unavailable delegation or visual tools.
Review all rendered pages and the current source after changes. Structural
checks and installed skills do not authenticate reviews or approve release.

Setup does not enable hooks, change global configuration, grant project trust,
initialize Git, or verify native discovery. Codex and Hermes may require a Git
project root for project discovery; Hermes additionally requires explicit
project trust. Inspect the installed skills and use your host's documented
trust/discovery procedure. Existing user instructions remain authoritative.
Optional hooks require separate `cv install-hooks` and host activation steps.
'''


def _selected(host):
    if host == 'all':
        return tuple(HOSTS)
    if host not in HOSTS:
        raise DeploymentError('Choose codex, claude, hermes or all.')
    return (host,)


def _payload():
    payload = {}
    for name in SKILLS:
        source = files('cv_toolkit').joinpath('assets', 'skills', name)
        if not source.joinpath('SKILL.md').is_file():
            raise DeploymentError('Packaged skills are incomplete; reinstall resume-toolkit.')
        payload[name] = {path.as_posix(): raw
                         for path, raw in _skill_resources(source, Path('.'))}
    return payload


def _conflict(host):
    return DeploymentError(
        f'{host} skill conflict in {HOSTS[host]}: an altered, partial or aliased '
        'toolkit skill set exists. Back up your changes, compare with the package, '
        'then move all four toolkit skill directories aside together and rerun '
        'setup. Unrelated skills can stay. No requested host was installed.'
    )


def _host_status(root, host, payload):
    """Accept either no owned skill directories or the exact complete bundle."""
    prefix = root / HOSTS[host]
    current = root
    for part in Path(HOSTS[host]).parts:
        current = current / part
        if current.is_symlink() or (current.exists() and not current.is_dir()):
            raise _conflict(host)
        if not current.resolve().is_relative_to(root):
            raise _conflict(host)
    present = [(prefix / name).exists() or (prefix / name).is_symlink() for name in SKILLS]
    if not any(present):
        return 'missing'
    if not all(present):
        raise _conflict(host)
    for name in SKILLS:
        folder = prefix / name
        if not folder.is_dir() or folder.is_symlink():
            raise _conflict(host)
        actual = {}
        for path in folder.rglob('*'):
            if path.is_symlink() or not path.resolve().is_relative_to(root):
                raise _conflict(host)
            if path.is_file():
                actual[path.relative_to(folder).as_posix()] = path.read_bytes()
        if actual != payload[name]:
            raise _conflict(host)
    return 'matching'


def _workspace(root):
    """Reuse the canonical onboarding route without allowing malformed records."""
    workspace = Workspace.load(root)
    state = classify(workspace.root)
    if state.state in {'unconfigured', 'malformed'}:
        raise DeploymentError(
            'Workspace configuration or profile records are invalid. Run cv doctor '
            '--workspace DIRECTORY, repair the indicated records, and rerun setup; '
            'existing candidate facts were not changed.'
        )
    # Onboarding intentionally routes synthetic/empty profiles early. Diagnose
    # malformed records in those states too, without treating fixtures as facts.
    registry_path = workspace.profile_dir / 'registry.json'
    raw_registry = load_json(registry_path) if registry_path.exists() else []
    registry = (build_source_registry(raw_registry) if isinstance(raw_registry, list)
                else _require_source_registry(raw_registry))
    projection = workspace.profile_dir / 'projection.json'
    if state.state != 'missing_candidate' or projection.exists():
        evidence = load_evidence(workspace.profile_dir / 'evidence.json', registry)
        if projection.exists():
            load_projection(projection, evidence, registry)
    return workspace, state


def setup(root, *, host, name='Candidate', example=None):
    """Preflight all requested hosts, then install without overwriting user files."""
    root = Path(root).expanduser().resolve()
    selected = _selected(host)
    payload = _payload()
    new = not root.exists() or (root.is_dir() and not any(root.iterdir()))
    if not new:
        if example is not None:
            raise DeploymentError(
                '--example only initializes a new or empty workspace. Choose a new '
                'directory for a demonstration, or omit --example to preserve and reuse this profile.'
            )
        try:
            _, state = _workspace(root)
        except (ValueError, OSError) as exc:
            if isinstance(exc, DeploymentError):
                raise
            raise DeploymentError(
                'The destination is not an empty directory or valid toolkit workspace. '
                'Choose a new private directory or repair cvtool.toml and profile records; '
                'nothing was changed.'
            ) from None
    statuses = {item: _host_status(root, item, payload) for item in selected}
    instruction_names = ['RESUME_TOOLKIT.md']
    if any(item in selected for item in ('codex', 'hermes')):
        instruction_names.append('AGENTS.md')
    if 'claude' in selected:
        instruction_names.append('CLAUDE.md')
    for filename in instruction_names:
        path = root / filename
        if path.exists() and not path.is_file():
            raise DeploymentError(
                f'{filename} is not a file. Move that path aside before setup; nothing was changed.'
            )
    if new:
        init_workspace(root, name=name, example=example)
        _, state = _workspace(root)
    hosts = {}
    for item, status in statuses.items():
        if status == 'missing':
            for skill, resources in payload.items():
                for relative, raw in resources.items():
                    target = root / HOSTS[item] / skill / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with target.open('xb') as stream:
                        stream.write(raw)
        hosts[item] = {'skills': 'installed' if status == 'missing' else 'unchanged',
                       'skill_count': len(SKILLS), 'runtime_discovery_verified': False}
    instructions = {}
    for filename in instruction_names:
        path = root / filename
        if path.exists() or path.is_symlink():
            instructions[filename] = 'preserved'
        else:
            body = _GUIDE if filename == 'RESUME_TOOLKIT.md' else (
                '# Resume Toolkit\n\nRead [RESUME_TOOLKIT.md](RESUME_TOOLKIT.md) and '
                'the selected workflow skill with its linked references.\n'
            )
            with path.open('x', encoding='utf-8', newline='\n') as stream:
                stream.write(body)
            instructions[filename] = 'created'
    return {'workspace': str(root), 'initialized': new, 'profile_preserved': not new,
            'state': state.state, 'skill': state.load_skill, 'guidance': state.action,
            'hosts': hosts, 'instructions': instructions,
            'startup_guide': str(root / 'RESUME_TOOLKIT.md'),
            'fallback_skill_paths': {item: str(root / HOSTS[item] / state.load_skill / 'SKILL.md')
                                     for item in selected},
            'runtime_discovery_verified': False, 'hooks_changed': False,
            'hooks_installed_by_setup': False,
            'next_step': 'Read RESUME_TOOLKIT.md and run cv doctor for this workspace and host.'}


def _git(root, *args):
    try:
        # check-ignore consumes literal filenames and rejects literal pathspec
        # magic; ls-files does accept pathspecs and needs the explicit flag.
        options = ['--literal-pathspecs'] if args[0] == 'ls-files' else []
        return subprocess.run(['git', '--no-optional-locks', *options,
                               '-C', str(root), *args], capture_output=True,
                              timeout=10, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None


def _ignore_check(workspace, git_root):
    relative = workspace.outputs_dir.relative_to(workspace.root).as_posix()
    rule_present = False
    ignore = workspace.root / '.gitignore'
    if ignore.is_file():
        lines = ignore.read_text(encoding='utf-8').splitlines()
        rule_present = any(line.strip() in {relative + '/', '/' + relative + '/'} for line in lines)
    base = {'id': 'output_ignore', 'directory': relative,
            'rule_present': rule_present, 'enforced': False}
    if git_root is None:
        return {**base, 'status': 'warning', 'message':
                'Git ignore enforcement is unverified without a usable repository. '
                'A literal workspace ignore rule is present.' if rule_present else
                'Git ignore enforcement is unverified; add the configured output directory to .gitignore.'}
    probe = str(workspace.outputs_dir / '.__resume_toolkit_ignore_probe__')
    ignored = _git(workspace.root, 'check-ignore', '-q', '--', probe)
    tracked = _git(workspace.root, 'ls-files', '-z', '--', str(workspace.outputs_dir))
    unignored = _git(workspace.root, 'ls-files', '--others', '--exclude-standard', '-z', '--',
                     str(workspace.outputs_dir))
    if (ignored is None or ignored.returncode not in (0, 1)
            or any(result is None or result.returncode != 0 for result in (tracked, unignored))):
        return {**base, 'status': 'warning', 'message':
                'Git could not verify output ignore rules; inspect the repository configuration.'}
    tracked_count = len([entry for entry in tracked.stdout.split(b'\0') if entry])
    unignored_count = len([entry for entry in unignored.stdout.split(b'\0') if entry])
    enforced = ignored.returncode == 0 and tracked_count == 0 and unignored_count == 0
    return {**base, 'status': 'pass' if enforced else 'error', 'enforced': enforced,
            'tracked_output_count': tracked_count, 'unignored_output_count': unignored_count,
            'message': 'Output contents are ignored and untracked.' if enforced else
            'Output contents are not fully ignored or are tracked; repair ignore/index rules before generating documents.'}


def doctor(root, *, host='all'):
    """Inspect deployment prerequisites without writing files or activating hosts."""
    from .render import _find_chromium

    root = Path(root).expanduser().resolve()
    selected = _selected(host)
    checks = []
    result = {'workspace': str(root), 'checks': checks, 'runtime_discovery_verified': False,
              'hook_execution_verified': False, 'independent_review_verified': False}
    workspace = None
    try:
        workspace, state = _workspace(root)
        result.update(state=state.state, skill=state.load_skill)
        checks.append({'id': 'workspace', 'status': 'pass', 'message': 'Workspace configuration is valid.'})
        checks.append({'id': 'onboarding', 'status': 'pass' if state.state == 'ready' else 'warning',
                       'message': state.action})
    except (ValueError, OSError):
        state = classify(root)
        result.update(state='unconfigured' if state.state == 'unconfigured' else 'malformed', skill='')
        checks.append({'id': 'workspace', 'status': 'error', 'message':
                       'Missing or invalid workspace configuration/profile. Run cv setup on a new '
                       'private directory, or repair the existing cvtool.toml and profile records.',
                       'guidance': state.action if state.state in {'unconfigured', 'malformed'} else
                       'Run cv validate-evidence and cv validate-projection to identify invalid records. '
                       'Repair records before capturing or drafting; do not invent candidate facts.'})
        workspace = None
    payload = _payload()
    for item in selected:
        try:
            status = _host_status(root, item, payload)
            checks.append({'id': f'skills.{item}', 'status': 'pass' if status == 'matching' else 'error',
                           'state': status, 'message': 'All packaged skills and references match.'
                           if status == 'matching' else f'Run cv setup DIRECTORY --host {item} to install skills.'})
        except (ValueError, OSError) as exc:
            checks.append({'id': f'skills.{item}', 'status': 'error', 'state': 'conflict',
                           'message': str(exc) if isinstance(exc, DeploymentError) else
                           'Skill files cannot be read; inspect filesystem permissions.'})
    for executable in ('cv', *selected):
        found = shutil.which(executable)
        checks.append({'id': f'cli.{executable}', 'status': 'pass' if found else 'warning',
                       'path': found, 'message': 'Executable found on PATH; runtime behavior is unverified.'
                       if found else 'Executable is not on PATH; activate/install the intended environment or use its absolute executable path.'})
    browser = _find_chromium()
    checks.append({'id': 'browser', 'status': 'pass' if browser else 'warning',
                   'path': str(browser) if browser else None, 'message':
                   'Chromium executable found; PDF rendering has not been exercised.' if browser else
                   'No Chromium executable found. HTML previews work; install Chrome/Edge/Chromium or set CV_CHROME_PATH for PDF rendering.'})
    git_root = None
    if shutil.which('git') and root.is_dir():
        discovery = _git(root, 'rev-parse', '--show-toplevel')
        if discovery is not None and discovery.returncode == 0:
            git_root = discovery.stdout.decode('utf-8', errors='replace').strip()
    checks.append({'id': 'git', 'status': 'pass' if git_root else 'warning', 'root': git_root,
                   'message': 'Git root found. Host discovery/trust still requires a real host session.' if git_root else
                   'No usable Git root found. Codex/Hermes project discovery may require one; create a private local repository or load skill files explicitly. No trust settings were changed.'})
    if 'hermes' in selected and git_root and Path(git_root).resolve() != root:
        checks.append({'id': 'hermes.project_root', 'status': 'warning', 'message':
                       'This workspace is below the Git project root. Hermes project discovery '
                       'looks at the root, so these workspace-local skills may not be discovered. '
                       'Use a dedicated private repository at this workspace root or read the '
                       'installed skill paths explicitly. No repository or trust settings were changed.'})
    if workspace is not None:
        checks.append(_ignore_check(workspace, git_root))
    result['status'] = 'invalid' if any(check['status'] == 'error' for check in checks) else 'ok'
    return result
