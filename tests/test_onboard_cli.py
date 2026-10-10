"""Public entry routing remains read-only and never upgrades malformed records."""
import json

from cv_toolkit.bootstrap import init_workspace
from cv_toolkit.cli import main
from cv_toolkit.onboarding import classify


def test_onboard_unconfigured_does_not_create_workspace(tmp_path, capsys):
    target = tmp_path / 'not-created'
    assert main(['onboard', '--workspace', str(target)]) == 0
    assert json.loads(capsys.readouterr().out)['state'] == 'unconfigured'
    assert not target.exists()


def test_onboard_empty_and_malformed(tmp_path, capsys):
    ws = init_workspace(tmp_path / 'ws')
    assert main(['onboard', '--workspace', str(ws)]) == 0
    assert json.loads(capsys.readouterr().out)['state'] == 'missing_candidate'
    evidence = ws / 'profile/evidence.json'
    evidence.write_text('{}', encoding='utf-8')
    assert main(['onboard', '--workspace', str(ws)]) == 2
    assert json.loads(capsys.readouterr().out)['state'] == 'malformed'
    assert evidence.read_text(encoding='utf-8') == '{}'


def test_missing_validator_never_claims_ready(tmp_path, monkeypatch):
    ws = init_workspace(tmp_path / 'ws')
    monkeypatch.setattr('cv_toolkit.onboarding._CANONICAL', False)
    assert classify(ws).state == 'malformed'
