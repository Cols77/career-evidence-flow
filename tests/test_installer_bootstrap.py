"""The checkout installer runs before third-party package imports are available."""
import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]


def loader():
    path = ROOT / 'install.py'
    assert path.is_file(), 'one-command installer is missing'
    spec = importlib.util.spec_from_file_location('career_evidence_installer', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_checkout_installer_is_available_without_importing_the_package():
    assert (ROOT / 'install.py').is_file(), 'one-command installer is missing'


@pytest.mark.parametrize('host', ['codex', 'claude', 'hermes'])
def test_each_host_has_a_help_entrypoint(host):
    loader()
    result = subprocess.run([sys.executable, '-I', str(ROOT / 'install.py'), host, '--help'],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0
    assert '--hooks' in result.stdout and '--project' in result.stdout


def test_unmanaged_runtime_is_never_reused(tmp_path):
    module = loader()
    environment = tmp_path / '.local/career-evidence-flow/venv'
    environment.mkdir(parents=True)
    (environment / 'keep.txt').write_text('Owner environment')
    with pytest.raises(ValueError):
        module.bootstrap('codex', tmp_path)
    assert (environment / 'keep.txt').read_text() == 'Owner environment'
    assert not (tmp_path / 'user-profile').exists()


def test_runtime_symlink_is_rejected(tmp_path):
    module = loader()
    external = tmp_path / 'external'
    external.mkdir()
    project = tmp_path / 'project'
    project.mkdir()
    try:
        (project / '.local').symlink_to(external, target_is_directory=True)
    except OSError:
        pytest.skip('symlink creation unavailable')
    with pytest.raises(ValueError):
        module.bootstrap('claude', project)
    assert not list(external.iterdir())


def test_parallel_bootstrap_cannot_share_a_runtime_writer(tmp_path, monkeypatch):
    module = loader()
    monkeypatch.setattr(module.venv, 'EnvBuilder', lambda **kwargs: pytest.fail('environment creation reached before lock validation'))
    lock = tmp_path / '.local/career-evidence-flow/bootstrap.lock'
    lock.parent.mkdir(parents=True)
    lock.write_text('another installer')
    with pytest.raises(ValueError, match='busy'):
        module.bootstrap('codex', tmp_path)
    assert lock.read_text() == 'another installer'
    assert not (lock.parent / 'venv').exists()


def test_malformed_runtime_inventory_is_reported_without_creating_environment(tmp_path, monkeypatch):
    import json
    module = loader()
    monkeypatch.setattr(module.venv, 'EnvBuilder', lambda **kwargs: pytest.fail('environment creation reached before inventory validation'))
    marker = tmp_path / '.local/career-evidence-flow/runtime.json'
    marker.parent.mkdir(parents=True)
    marker.write_text(json.dumps({'schema_version': 1, 'project': str(tmp_path),
                                  'environment': module.RUNTIME}))
    with pytest.raises(ValueError, match='inventory'):
        module.bootstrap('claude', tmp_path)
    assert not (marker.parent / 'venv').exists()


@pytest.mark.parametrize('previous_visual', [False, True])
def test_missing_owned_environment_reinstalls_package_even_with_current_marker(tmp_path, monkeypatch, previous_visual):
    import json
    import os
    module = loader()
    marker = tmp_path / module.MARKER
    marker.parent.mkdir(parents=True)
    marker.write_text(json.dumps({'schema_version': 1, 'project': str(tmp_path), 'environment': module.RUNTIME,
                                  'package_fingerprint': 'a' * 64, 'visual': previous_visual}))
    class Builder:
        def create(self, root):
            python = root / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
            python.parent.mkdir(parents=True)
            python.write_bytes(b'placeholder for isolated bootstrap test')
    calls = []
    monkeypatch.setattr(module.venv, 'EnvBuilder', lambda **kwargs: Builder())
    monkeypatch.setattr(module, '_fingerprint', lambda: 'a' * 64)
    monkeypatch.setattr(module, '_command', lambda argv: {'status': 'ok'})
    monkeypatch.setattr(module.subprocess, 'run', lambda argv, **kwargs: calls.append(argv))
    result = module.bootstrap('codex', tmp_path, visual=False)
    assert result['package_updated'] is True
    assert len(calls) == 1 and calls[0][1:5] == ['-m', 'pip', 'install', '--upgrade']
    assert json.loads(marker.read_text())['visual'] is False


def test_interrupted_ensurepip_is_retried_even_when_python_exists(tmp_path, monkeypatch):
    import json
    import os
    module = loader()
    marker = tmp_path / module.MARKER
    marker.parent.mkdir(parents=True)
    marker.write_text(json.dumps({'schema_version': 1, 'project': str(tmp_path), 'environment': module.RUNTIME,
                                  'package_fingerprint': None, 'visual': False}))
    environment = tmp_path / module.RUNTIME
    python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    python.parent.mkdir(parents=True)
    python.write_bytes(b'Python exists but ensurepip was interrupted')
    creations = []
    class Builder:
        def create(self, root):
            creations.append(root)
    monkeypatch.setattr(module.venv, 'EnvBuilder', lambda **kwargs: Builder())
    monkeypatch.setattr(module, '_fingerprint', lambda: 'a' * 64)
    monkeypatch.setattr(module, '_command', lambda argv: {'status': 'ok'})
    monkeypatch.setattr(module.subprocess, 'run', lambda argv, **kwargs: None)
    module.bootstrap('claude', tmp_path, visual=False)
    assert creations == [environment]
