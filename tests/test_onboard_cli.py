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


def test_explicit_workspace_routing_does_not_reuse_process_cwd(tmp_path, monkeypatch, capsys):
    empty = init_workspace(tmp_path / 'empty')
    synthetic = init_workspace(tmp_path / 'synthetic', example='developer')
    monkeypatch.chdir(synthetic)
    before = {p: p.read_bytes() for root in (empty, synthetic)
              for p in root.rglob('*') if p.is_file()}
    for root, expected in ((empty, 'missing_candidate'), (synthetic, 'synthetic'),
                           (empty, 'missing_candidate')):
        assert main(['onboard', '--workspace', str(root)]) == 0
        result = json.loads(capsys.readouterr().out)
        assert result['state'] == expected
        assert result['skill'] == 'experience-capture'
    after = {p: p.read_bytes() for root in (empty, synthetic)
             for p in root.rglob('*') if p.is_file()}
    assert after == before
