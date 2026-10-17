"""Job discovery is available through each host without creating an application."""
import pytest

from cv_toolkit.bootstrap import init_workspace, install_skills
from cv_toolkit.codex_hooks import checkpoint_status, dispatch, record_checkpoint


@pytest.mark.parametrize('host,prefix', [
    ('codex', '.agents'), ('claude', '.claude'), ('hermes', '.hermes'),
])
def test_job_search_installs_with_records_reference(tmp_path, host, prefix):
    workspace = init_workspace(tmp_path / 'private')
    install_skills(workspace, host)
    skill = workspace / prefix / 'skills/job-search'
    assert (skill / 'SKILL.md').is_file()
    assert (skill / 'references/search-records.md').is_file()
    assert not list((workspace / 'applications').iterdir())


def test_search_checkpoint_restores_without_application_or_approval(tmp_path):
    workspace = init_workspace(tmp_path / 'private')
    record_checkpoint(workspace, 'search-session', 'job-search', 'working', [])
    result = dispatch(dict(session_id='search-session', cwd=str(workspace),
                           hook_event_name='SessionStart', source='compact'), workspace)
    assert 'job-search' in result['hookSpecificOutput']['additionalContext']
    state = checkpoint_status(workspace, 'search-session')
    assert state['release_available'] is False
    assert state['review_status'] == 'unreviewed_preview'
    assert not list((workspace / 'applications').iterdir())
