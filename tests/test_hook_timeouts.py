"""Installed host definitions must allow slow local startup and file checks."""
import json

import pytest

from cv_toolkit.bootstrap import init_workspace, install_entry_hook


@pytest.mark.parametrize('host,config', [
    ('codex', '.codex/hooks.json'),
    ('claude', '.claude/settings.local.json'),
])
def test_installed_hooks_allow_two_minutes_except_codex_interrupt(tmp_path, host, config):
    project = tmp_path / 'project'
    project.mkdir()
    workspace = init_workspace(project / 'user-profile')
    install_entry_hook(workspace, host, project_root=project)
    definitions = json.loads((project / config).read_text(encoding='utf-8'))['hooks']
    assert definitions
    for event, groups in definitions.items():
        for group in groups:
            for handler in group['hooks']:
                # Codex imposes a three-second maximum on Interrupt handlers.
                expected = 3 if host == 'codex' and event == 'Interrupt' else 120
                assert handler['timeout'] == expected, (host, event)
