"""Managed project integrations; local ownership metadata is not host trust."""
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shlex
import tempfile
from uuid import uuid4

from . import deployment
from .bootstrap import (SKILLS, _hook_resources, claude_hook_payload,
                        codex_hook_payload, workspace_project_root)
from .records import ToolkitError, confined, load_json, object_fields, schema


PREFIXES = deployment.HOSTS
_CONFIGS = {'codex': '.codex/hooks.json', 'claude': '.claude/settings.local.json'}
_BUNDLES = {'codex': '.codex/hooks/resume-toolkit',
            'claude': '.claude/hooks/resume-toolkit', 'hermes': '.hermes/plugins/resume-toolkit'}


def _hash(raw):
    return sha256(raw).hexdigest()


def _json(raw):
    return (json.dumps(raw, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def _plain(project, relative):
    path = project / relative
    result = confined(project, relative, required=False)
    current = project
    for part in Path(relative).parts:
        current = current / part
        if current.is_symlink() or (current.exists() and current.resolve() != current):
            raise ToolkitError('installation aliases are unsupported')
    if result != path:
        raise ToolkitError('installation aliases are unsupported')
    return result


def _write_bytes(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.install-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _skills_payload(host):
    return {f'{PREFIXES[host]}/{name}/{relative}': raw
            for name, entries in deployment._payload().items() for relative, raw in entries.items()}


def _hooks_payload(host, workspace, project):
    if host == 'hermes':
        entries = dict(_hook_resources())
        entries['binding.json'] = (json.dumps({'workspace': workspace.relative_to(project).as_posix()}) + '\n').encode('utf-8')
        return {f'{_BUNDLES[host]}/{p}': raw for p, raw in entries.items()}, None, {}
    entries = (codex_hook_payload if host == 'codex' else claude_hook_payload)(workspace, project)
    config = _CONFIGS[host]
    groups = json.loads(entries.pop(config))['hooks']
    return entries, config, groups


def _roots(host, hooks):
    return [f'{PREFIXES[host]}/{name}' for name in SKILLS] + ([_BUNDLES[host]] if hooks else [])


def _allowed(relative, roots):
    return isinstance(relative, str) and any(relative.startswith(root + '/') for root in roots)


def _inventory(path, host, workspace, project):
    if not path.exists():
        return None
    record = load_json(path)
    object_fields(record, {'schema_version', 'host', 'workspace', 'hooks', 'files', 'configs'}, rule='installation inventory')
    schema(record['schema_version'])
    if record['host'] != host or record['workspace'] != workspace.relative_to(project).as_posix() or type(record['hooks']) is not bool:
        raise ToolkitError('installation inventory binding mismatch')
    if not isinstance(record['files'], dict) or not record['files'] or not isinstance(record['configs'], dict):
        raise ToolkitError('invalid installation inventory')
    for relative, fingerprint in record['files'].items():
        if not _allowed(relative, _roots(host, record['hooks'])) or not isinstance(fingerprint, str) or not re.fullmatch('[a-f0-9]{64}', fingerprint):
            raise ToolkitError('invalid managed installation path or hash')
        _plain(project, relative)
    if set(record['configs']) != ({_CONFIGS[host]} if record['hooks'] and host in _CONFIGS else set()):
        raise ToolkitError('invalid managed config path')
    if record['configs']:
        _validate_owned_groups(record['configs'][_CONFIGS[host]], host, workspace, project)
    return record


def _validate_owned_groups(events, host, workspace, project):
    """An inventory may claim only this toolkit's narrow generated hook form."""
    from . import codex_hooks, claude_hooks
    allowed = codex_hooks.EVENTS if host == 'codex' else claude_hooks.EVENTS
    runner = str(project / _BUNDLES[host] / 'run.py')
    expected_args = ['-I', runner, '--workspace', str(workspace)]
    if not isinstance(events, dict) or not events or set(events) - set(allowed):
        raise ToolkitError('invalid owned hook events')
    for groups in events.values():
        if not isinstance(groups, list) or len(groups) != 1:
            raise ToolkitError('invalid owned hook groups')
        group = groups[0]
        object_fields(group, {'hooks'}, rule='owned hook group')
        if not isinstance(group['hooks'], list) or len(group['hooks']) != 1:
            raise ToolkitError('invalid owned hook handlers')
        handler = group['hooks'][0]
        fields = {'type', 'command', 'timeout', 'commandWindows' if host == 'codex' else 'args'}
        object_fields(handler, fields, rule='owned hook handler')
        if handler['type'] != 'command' or type(handler['timeout']) is not int or handler['timeout'] <= 0:
            raise ToolkitError('invalid owned hook handler values')
        if not isinstance(handler['command'], str):
            raise ToolkitError('invalid owned hook command')
        if host == 'claude':
            if handler['args'] != expected_args or not Path(handler['command']).is_absolute():
                raise ToolkitError('inventory cannot claim another hook command')
        else:
            argv = shlex.split(handler['command'])
            if len(argv) != 5 or argv[1:] != expected_args or not Path(argv[0]).is_absolute():
                raise ToolkitError('inventory cannot claim another hook command')
            windows = '& ' + ' '.join("'" + arg.replace("'", "''") + "'" for arg in argv)
            if handler['commandWindows'] != windows:
                raise ToolkitError('inventory cannot claim another Windows hook command')


def _merge_groups(current, previous, desired, runner):
    if not isinstance(current, dict) or not isinstance(current.get('hooks', {}), dict):
        raise ToolkitError('invalid host hook settings')
    result = deepcopy(current)
    hooks = result.setdefault('hooks', {})
    if any(not isinstance(groups, list) for groups in hooks.values()) or not isinstance(previous, dict):
        raise ToolkitError('invalid host hook groups')
    for event, groups in previous.items():
        if not isinstance(groups, list):
            raise ToolkitError('invalid managed hook groups')
        for group in groups:
            if hooks.get(event, []).count(group) != 1:
                raise ToolkitError('managed hook group was edited or removed; compare before upgrading')
            hooks[event].remove(group)
    def refers(value):
        if isinstance(value, str):
            return runner.casefold() in value.replace('\\', '/').casefold()
        if isinstance(value, dict):
            return any(refers(v) for v in value.values())
        if isinstance(value, list):
            return any(refers(v) for v in value)
        return False
    # Exact current package groups may be adopted from a legacy installation.
    for event, groups in desired.items():
        for group in groups:
            if not previous and hooks.get(event, []).count(group) == 1:
                hooks[event].remove(group)
    if any(refers(group) for groups in hooks.values() for group in groups):
        raise ToolkitError('unmanaged toolkit hook group exists; compare before adopting')
    for event, groups in desired.items():
        hooks.setdefault(event, []).extend(deepcopy(groups))
    return result


def _ignore_bytes(project, workspace, host, hooks):
    path = _plain(project, '.gitignore')
    raw = path.read_bytes() if path.exists() else b''
    text = raw.decode('utf-8')
    relative = workspace.relative_to(project).as_posix()
    # Git-ignore metacharacters must represent literal workspace components.
    relative = ''.join('\\' + c if c in '*?[]' else c for c in relative)
    entries = [f'/{relative}/', '/.local/', '/RESUME_TOOLKIT.md']
    if hooks:
        entries += ['/' + _BUNDLES[host] + '/']
        if host in _CONFIGS:
            entries += ['/' + _CONFIGS[host]]
    missing = [entry for entry in entries if entry not in text.splitlines()]
    if not missing:
        return raw
    return (text.rstrip('\n') + '\n\n# Career Evidence Flow local installation\n' + '\n'.join(missing) + '\n').encode('utf-8')


def _other_hosts(project, workspace, selected):
    attention = []
    for host in PREFIXES:
        if host == selected:
            continue
        try:
            path = _plain(project, f'.local/resume-toolkit/installations/{host}.json')
            if not path.exists():
                continue
            prior = _inventory(path, host, workspace, project)
            expected = _skills_payload(host)
            config, groups = None, {}
            if prior['hooks']:
                hook_files, config, groups = _hooks_payload(host, workspace, project)
                expected.update(hook_files)
            fingerprints = {p: _hash(raw) for p, raw in expected.items()}
            if (prior['files'] != fingerprints or prior['configs'] != ({config: groups} if config else {})
                    or any(not _plain(project, p).is_file() or _plain(project, p).read_bytes() != raw for p, raw in expected.items())):
                attention.append(host)
        except (OSError, ValueError, RuntimeError):
            attention.append(host)
    return attention


@contextmanager
def _lock(project):
    path = _plain(project, '.local/resume-toolkit/install.lock')
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        stream = path.open('xb')
    except OSError:
        raise ToolkitError('installation is busy; inspect the installer lock') from None
    try:
        stream.close()
        yield
    finally:
        path.unlink()


def install_agent(workspace, *, host, project_root, hooks=False):
    """Install or refresh owned resources without replacing owner modifications."""
    if host not in PREFIXES or type(hooks) is not bool:
        raise ToolkitError('invalid installer host or hook option')
    project = Path(project_root).expanduser().resolve(strict=True)
    workspace = Path(workspace).expanduser().absolute()
    workspace_project_root(workspace, project)
    if workspace == project:
        raise ToolkitError('installer requires a contained private workspace directory')
    workspace = _plain(project, workspace.relative_to(project).as_posix())
    if workspace.exists() and any(workspace.iterdir()):
        deployment._workspace(workspace)
    guide = _plain(project, 'RESUME_TOOLKIT.md')
    if guide.is_file() and guide.read_text(encoding='utf-8').startswith('# Resume Toolkit workspace'):
        expected = deployment._guide(workspace, project, host)
        commands = [line for line in expected.splitlines() if 'cv_toolkit.cli' in line and '-m' in line]
        if commands[-1] not in guide.read_text(encoding='utf-8'):
            raise ToolkitError('existing startup guide pins another environment; preserve and compare it before reinstalling')
    with _lock(project):
        inventory_path = _plain(project, f'.local/resume-toolkit/installations/{host}.json')
        previous = _inventory(inventory_path, host, workspace, project)
        effective_hooks = hooks or bool(previous and previous['hooks'])
        skills = _skills_payload(host)
        desired = dict(skills)
        config, groups = None, {}
        if effective_hooks:
            hook_files, config, groups = _hooks_payload(host, workspace, project)
            desired.update(hook_files)
        old_files = previous['files'] if previous else {}
        roots = _roots(host, effective_hooks)
        actual = set()
        for relative in roots:
            folder = _plain(project, relative)
            if folder.exists():
                if not folder.is_dir():
                    raise ToolkitError('managed integration directory is obstructed')
                for path in folder.rglob('*'):
                    if '__pycache__' in path.parts:
                        continue
                    relative_path = path.relative_to(project).as_posix()
                    _plain(project, relative_path)
                    if path.is_file():
                        actual.add(relative_path)
        if actual - desired.keys() - old_files.keys():
            raise ToolkitError('unexpected file in managed integration; preserve and compare it')
        changes, originals = {}, {}
        for relative in sorted(set(desired) | set(old_files)):
            path = _plain(project, relative)
            raw = path.read_bytes() if path.is_file() else None
            if relative in old_files and (raw is None or _hash(raw) != old_files[relative]) and raw != desired.get(relative):
                raise ToolkitError('managed integration was edited or removed; preserve and compare it')
            if raw is not None and raw != desired.get(relative) and relative not in old_files:
                raise ToolkitError('unmanaged integration differs from package; preserve and compare it')
            if raw != desired.get(relative):
                changes[relative] = desired.get(relative)
                originals[relative] = raw
        configs = {}
        if config:
            path = _plain(project, config)
            raw = path.read_bytes() if path.exists() else None
            current = load_json(path) if raw is not None else {}
            old_groups = previous['configs'].get(config, {}) if previous else {}
            merged = _merge_groups(current, old_groups, groups, (project / _BUNDLES[host] / 'run.py').as_posix())
            configs[config] = groups
            if merged != current:
                changes[config], originals[config] = _json(merged), raw
        ignore = _plain(project, '.gitignore')
        raw = ignore.read_bytes() if ignore.exists() else None
        updated_ignore = _ignore_bytes(project, workspace, host, effective_hooks)
        if raw != updated_ignore:
            changes['.gitignore'], originals['.gitignore'] = updated_ignore, raw
        record = {'schema_version': 1, 'host': host, 'workspace': workspace.relative_to(project).as_posix(),
                  'hooks': effective_hooks, 'files': {p: _hash(raw) for p, raw in desired.items()}, 'configs': configs}
        inventory_relative = inventory_path.relative_to(project).as_posix()
        prior_inventory = inventory_path.read_bytes() if inventory_path.exists() else None
        if previous != record:
            changes[inventory_relative], originals[inventory_relative] = _json(record), prior_inventory
        backup = _plain(project, '.local/resume-toolkit/install-backups/' + uuid4().hex)
        written = []
        try:
            # Save recovery bytes before touching installed files. Backups use
            # private temporary-file permissions and remain outside discovery.
            for relative, raw in originals.items():
                if raw is not None:
                    _write_bytes(backup / relative, raw)
            for relative in sorted(changes, key=lambda p: p == inventory_relative):
                if relative == inventory_relative:
                    continue
                path = _plain(project, relative)
                current = path.read_bytes() if path.is_file() else None
                if current != originals[relative]:
                    raise ToolkitError('integration changed during installation')
                if changes[relative] is None:
                    path.unlink()
                else:
                    _write_bytes(path, changes[relative])
                written.append(relative)
            setup = deployment.setup(workspace, host=host, project_root=project)
            if inventory_relative in changes:
                _write_bytes(inventory_path, changes[inventory_relative])
                written.append(inventory_relative)
        except (OSError, ValueError, RuntimeError):
            conflicts = []
            for relative in reversed(written):
                path = _plain(project, relative)
                raw = originals[relative]
                current = path.read_bytes() if path.is_file() else None
                if current != changes[relative]:
                    conflicts.append(relative)
                    continue
                if raw is None:
                    path.unlink(missing_ok=True)
                else:
                    _write_bytes(path, raw)
            if conflicts:
                raise ToolkitError('installation failed; concurrent edits were preserved, inspect recovery backups') from None
            raise
        skill_changed = any(p in changes for p in skills)
        hook_changed = effective_hooks and any(p in changes for p in set(desired) - set(skills) | ({config} if config else set()))
        return {'host': host, 'workspace': str(workspace), 'project_root': str(project),
                'skills': ('updated' if previous else 'installed') if skill_changed else 'unchanged',
                'hooks': (('updated' if previous and previous['hooks'] else 'installed') if hook_changed else 'unchanged') if effective_hooks else 'not_requested',
                'inventory': inventory_relative, 'backup': str(backup) if backup.exists() else None,
                'startup_guide': setup['startup_guide'], 'runtime_discovery_verified': False,
                'other_hosts_needing_attention': _other_hosts(project, workspace, host),
                'trust_changed': False, 'profile_preserved': True,
                'next_step': 'Read RESUME_TOOLKIT.md, inspect installed integrations, then start the selected host from the project root. Host trust and plugin activation are explicit.'}
