#!/usr/bin/env python3
"""One-command Career Evidence Flow installer. Requires only Python 3.11+."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import venv


SOURCE = Path(__file__).resolve().parent
RUNTIME = '.local/career-evidence-flow/venv'
MARKER = '.local/career-evidence-flow/runtime.json'


def _plain(project, relative):
    path = project / relative
    current = project
    for part in Path(relative).parts:
        if part in {'.', '..'}:
            raise ValueError('Installer paths must stay inside the project.')
        current = current / part
        if current.is_symlink() or (current.exists() and current.resolve() != current):
            raise ValueError('Installer paths must not use symlinks or junctions.')
    if not path.resolve().is_relative_to(project):
        raise ValueError('Installer path escapes the project.')
    return path


def _write(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.bootstrap-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(raw)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _fingerprint():
    paths = [SOURCE / name for name in ('pyproject.toml', 'README.md', 'MANIFEST.in')]
    paths += [p for p in (SOURCE / 'src/cv_toolkit').rglob('*')
              if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc']
    digest = sha256()
    for path in sorted(paths):
        if path.is_symlink():
            raise ValueError('Package source aliases are unsupported.')
        digest.update(path.relative_to(SOURCE).as_posix().encode('utf-8') + b'\0')
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _command(argv):
    result = subprocess.run(argv, capture_output=True, text=True, timeout=240, check=False)
    if result.returncode:
        try:
            error = json.loads(result.stdout).get('error', 'Local installer command failed.')
        except ValueError:
            error = 'Local installer command failed; inspect the selected environment.'
        raise ValueError(error)
    return json.loads(result.stdout)


def bootstrap(host, project, *, hooks=False, visual=True, workspace='user-profile'):
    project = Path(project).expanduser().resolve(strict=True)
    lock = _plain(project, '.local/career-evidence-flow/bootstrap.lock')
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        stream = lock.open('xb')
    except OSError:
        raise ValueError('Project runtime installer is busy; inspect its bootstrap lock.') from None
    try:
        stream.close()
        return _bootstrap(host, project, hooks=hooks, visual=visual, workspace=workspace)
    finally:
        lock.unlink()


def _bootstrap(host, project, *, hooks=False, visual=True, workspace='user-profile'):
    if sys.version_info < (3, 11):
        raise ValueError('Python 3.11 or newer is required.')
    if host not in {'codex', 'claude', 'hermes'}:
        raise ValueError('Choose codex, claude or hermes.')
    project = Path(project).expanduser().resolve(strict=True)
    if not project.is_dir() or not (SOURCE / 'pyproject.toml').is_file():
        raise ValueError('Run this installer from a complete checkout and select an existing project.')
    raw_workspace = Path(workspace)
    if raw_workspace.is_absolute() or any(p in {'.', '..'} for p in raw_workspace.parts) or not raw_workspace.parts:
        raise ValueError('Workspace must be a project-relative child directory.')
    data = _plain(project, raw_workspace.as_posix())
    environment = _plain(project, RUNTIME)
    marker = _plain(project, MARKER)
    existing = None
    if marker.exists():
        existing = json.loads(marker.read_text(encoding='utf-8'))
        fields = {'schema_version', 'project', 'environment', 'package_fingerprint', 'visual'}
        if (not isinstance(existing, dict) or set(existing) != fields
                or type(existing['schema_version']) is not int or existing['schema_version'] != 1
                or existing['project'] != str(project) or existing['environment'] != RUNTIME
                or type(existing['visual']) is not bool
                or (existing['package_fingerprint'] is not None and (not isinstance(existing['package_fingerprint'], str)
                    or not re.fullmatch('[a-f0-9]{64}', existing['package_fingerprint'])))):
            raise ValueError('Runtime inventory conflicts with this project; preserve and inspect it.')
    elif environment.exists():
        raise ValueError('An unmanaged environment already exists; preserve it and choose a fresh project runtime.')
    ignore = _plain(project, '.gitignore')
    contents = ignore.read_text(encoding='utf-8') if ignore.exists() else ''
    if '/.local/' not in contents.splitlines() and '.local/' not in contents.splitlines():
        _write(ignore, (contents.rstrip('\n') + '\n/.local/\n').encode('utf-8'))
    state = existing or {'schema_version': 1, 'project': str(project), 'environment': RUNTIME,
                         'package_fingerprint': None, 'visual': False}
    if existing is None:
        _write(marker, (json.dumps(state, indent=2) + '\n').encode('utf-8'))
    python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not python.is_file() or state['package_fingerprint'] is None:
        # A prior successful marker must not survive loss or interrupted
        # recreation of its environment; every recovery must reinstall package bytes.
        state['package_fingerprint'] = None
        state['visual'] = False
        _write(marker, (json.dumps(state, indent=2) + '\n').encode('utf-8'))
        print('Creating the private project environment...', file=sys.stderr)
        venv.EnvBuilder(with_pip=True).create(environment)
    fingerprint = _fingerprint()
    updated = state['package_fingerprint'] != fingerprint or (visual and not state['visual'])
    if updated:
        print('Installing Career Evidence Flow and its Python dependencies...', file=sys.stderr)
        source = str(SOURCE) + ('[visual]' if visual else '')
        subprocess.run([str(python), '-m', 'pip', 'install', '--upgrade', source],
                       stdout=sys.stderr, stderr=sys.stderr, check=True, timeout=1200)
        state.update(package_fingerprint=fingerprint, visual=visual or state['visual'])
        _write(marker, (json.dumps(state, indent=2) + '\n').encode('utf-8'))
    command = [str(python), '-m', 'cv_toolkit.cli']
    args = ['--workspace', str(data), '--project-root', str(project), '--host', host]
    installed = _command([*command, 'install-agent', *args, *(['--hooks'] if hooks else [])])
    diagnostics = _command([*command, 'doctor', *args])
    return {'status': 'ok', 'host': host, 'environment': str(environment),
            'package_updated': updated, 'installation': installed, 'diagnostics': diagnostics,
            'native_host_execution_verified': False,
            'next_step': 'Read RESUME_TOOLKIT.md and start the selected agent from the project root. Configure its provider and trust explicitly.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('host', choices=('codex', 'claude', 'hermes'))
    parser.add_argument('--project', type=Path, default=SOURCE, help='Existing host project directory; defaults to this checkout')
    parser.add_argument('--workspace', default='user-profile', help='Private child directory relative to the project')
    parser.add_argument('--hooks', action='store_true', help='Install optional advisory hook files; host trust remains explicit')
    parser.add_argument('--without-visual', action='store_true', help='Omit optional PDF page-image dependencies')
    args = parser.parse_args(argv)
    try:
        result = bootstrap(args.host, args.project, hooks=args.hooks,
                           visual=not args.without_visual, workspace=args.workspace)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        result = {'status': 'invalid', 'error': str(error)}
    print(json.dumps(result, sort_keys=True))
    return 0 if result['status'] == 'ok' else 2


if __name__ == '__main__':
    raise SystemExit(main())
