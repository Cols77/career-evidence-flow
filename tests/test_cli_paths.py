import json

from cv_toolkit.cli import main


def test_cli_defaults_follow_configured_profile_directory(tmp_path, capsys):
    root = tmp_path / 'example'
    assert main(['init', str(root), '--example', 'developer']) == 0
    capsys.readouterr()
    (root / 'profile').rename(root / 'candidate-records')
    config = root / 'cvtool.toml'
    config.write_text(config.read_text().replace('profile = "profile"', 'profile = "candidate-records"'))
    assert main(['validate-evidence', '--workspace', str(root)]) == 0
    assert json.loads(capsys.readouterr().out)['claim_count'] == 4
    assert main(['validate-projection', '--workspace', str(root)]) == 0


def test_cli_answer_requires_known_provenance_before_writing(tmp_path, capsys):
    root = tmp_path / 'example'
    main(['init', str(root), '--example', 'developer'])
    capsys.readouterr()
    question = {'schema_version': 1, 'questions': [{'id': 'question.scope', 'prompt': 'Scope?', 'reason': 'Material', 'unlocks': [], 'status': 'pending', 'material': True}]}
    path = root / 'questions.json'
    path.write_text(json.dumps(question))
    original = path.read_bytes()
    args = ['answer', '--workspace', str(root), '--questions', 'questions.json', '--question-id', 'question.scope', '--text', 'Actual answer', '--source-id', 'source.missing', '--recorded-at', '2026-10-10T00:00:00Z']
    assert main(args) == 2
    assert path.read_bytes() == original
    args[args.index('source.missing')] = 'source.owner'
    assert main(args) == 0
    assert json.loads(path.read_text())['questions'][0]['answer']['text'] == 'Actual answer'


def test_html_output_is_preserved_when_replacement_fails(tmp_path, capsys, monkeypatch):
    root = tmp_path / 'example'
    main(['init', str(root), '--example', 'developer'])
    capsys.readouterr()
    output = root / 'outputs/resume.html'
    output.write_bytes(b'previous exact preview bytes')
    def reject_replace(*args):
        raise OSError('synthetic storage failure')
    monkeypatch.setattr('os.replace', reject_replace)
    assert main(['render', '--workspace', str(root), '--source', 'resume.md', '--output', 'outputs/resume.html']) == 2
    assert output.read_bytes() == b'previous exact preview bytes'
    assert sorted(p.name for p in output.parent.iterdir()) == ['resume.html']
