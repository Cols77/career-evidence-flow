"""Installed acceptance includes explicit project/data roots and real adapters."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys

from cv_toolkit.cli import main


ROOT = Path(__file__).resolve().parents[1]


def load_tool(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_release_allowlist_contains_all_standalone_adapter_modules():
    tool = load_tool('build_release')
    sources = tool.release_sources(ROOT)
    assert 'src/cv_toolkit/claude_hooks.py' in sources
    assert 'src/cv_toolkit/hook_scope.py' in sources
    assert 'src/cv_toolkit/page_layout.py' in sources
    assert 'src/cv_toolkit/application_tools.py' in sources


def test_verifier_exercises_reusable_application_commands(tmp_path):
    def command(*args):
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            assert main(list(args)) == 0
        return json.loads(captured.getvalue())
    root = tmp_path / 'fictional'
    command('init', str(root), '--example', 'developer')
    result = load_tool('verify_installed').verify_application_bundle(root, command)
    assert result == {'status': 'pass', 'review_status': 'unreviewed_preview', 'freshness': 'fresh'}


def test_verifier_executes_split_workspace_adapters_and_rejects_wrong_scopes(tmp_path):
    def command(*args):
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            assert main(list(args)) == 0
        return json.loads(captured.getvalue())

    tool = load_tool('verify_installed')
    result = tool.verify_project_deployment(tmp_path / 'single project', command, sys.executable)
    assert result['status'] == 'pass'
    assert result['standard_profile_schema'] is True
    assert result['repeat_setup_read_only'] is True
    assert result['native_host_execution'] == 'unverified'
    assert set(result['adapters']) == {'codex', 'claude', 'hermes'}
    for report in result['adapters'].values():
        assert report['bound_workspace_context'] == 'pass'
        assert report['foreign_scope_rejected'] == 'pass'
        assert report['execution_kind'] == 'manual_adapter_process'
