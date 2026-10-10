import json
from pathlib import Path

from cv_toolkit.cli import main


def test_init_refuses_nonempty_and_does_not_fabricate_evidence(tmp_path, capsys):
    root = tmp_path / 'candidate'
    assert main(['init', str(root), '--name', 'Synthetic Candidate']) == 0
    assert json.loads(capsys.readouterr().out)['status'] == 'ok'
    assert json.loads((root / 'profile/evidence.json').read_text())['items'] == []
    before = (root / 'cvtool.toml').read_bytes()
    assert main(['init', str(root), '--name', 'Replacement']) == 2
    assert (root / 'cvtool.toml').read_bytes() == before
    assert 'Replacement' not in capsys.readouterr().out


def test_two_synthetic_examples_validate_and_render_from_outside_workspace(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for name in ('developer', 'researcher'):
        root = tmp_path / name
        assert main(['init', str(root), '--example', name]) == 0
        capsys.readouterr()
        assert main(['validate-evidence', '--workspace', str(root), '--evidence', 'profile/evidence.json', '--registry', 'profile/registry.json']) == 0
        assert json.loads(capsys.readouterr().out)['claim_count'] >= 3
        assert main(['validate-projection', '--workspace', str(root), '--projection', 'profile/projection.json']) == 0
        capsys.readouterr()
        assert main(['render', '--workspace', str(root), '--source', 'resume.md', '--output', 'outputs/resume.html', '--format', 'html']) == 0
        html = (root / 'outputs/resume.html').read_text(encoding='utf-8')
        assert '<html' in html
        assert main(['check', '--workspace', str(root), '--document', 'outputs/resume.html']) == 0
        capsys.readouterr()
        assert main(['render', '--workspace', str(root), '--source', 'letter.md', '--output', 'outputs/letter.html', '--kind', 'cover_letter', '--format', 'html']) == 0
        capsys.readouterr()
        assert main(['check', '--workspace', str(root), '--document', 'outputs/letter.html', '--kind', 'cover_letter']) == 0
        capsys.readouterr()


def test_confined_cli_output_never_writes_outside_root(tmp_path, capsys):
    root = tmp_path / 'example'
    assert main(['init', str(root), '--example', 'developer']) == 0
    capsys.readouterr()
    assert main(['render', '--workspace', str(root), '--source', 'resume.md', '--output', '../escaped.html', '--format', 'html']) == 2
    assert not (tmp_path / 'escaped.html').exists()
    assert 'resume.md' not in capsys.readouterr().out


def test_skill_installation_refuses_overwriting_existing_files(tmp_path, capsys):
    root = tmp_path / 'candidate'
    assert main(['init', str(root), '--example', 'researcher']) == 0
    capsys.readouterr()
    assert main(['install-skills', '--workspace', str(root), '--host', 'codex']) == 0
    skill = root / '.agents/skills/experience-capture/SKILL.md'
    assert skill.is_file()
    assert 'cv validate-evidence' in skill.read_text()
    capsys.readouterr()
    skill.write_text('user customized')
    assert main(['install-skills', '--workspace', str(root), '--host', 'codex']) == 2
    assert skill.read_text() == 'user customized'


def test_unknown_registry_duplicate_keys_fail_safely(tmp_path, capsys):
    root = tmp_path / 'example'
    main(['init', str(root), '--example', 'developer'])
    capsys.readouterr()
    (root / 'profile/registry.json').write_text('{"secret":1,"secret":2}')
    assert main(['validate-evidence', '--workspace', str(root), '--evidence', 'profile/evidence.json', '--registry', 'profile/registry.json']) == 2
    assert 'secret' not in capsys.readouterr().out


def test_application_freezes_exact_supplied_job_bytes(tmp_path, capsys):
    root = tmp_path / 'example'
    main(['init', str(root), '--example', 'developer'])
    capsys.readouterr()
    original = b'Build tests\r\nUse Python.\r\n'
    (root / 'job.txt').write_bytes(original)
    assert main(['create-application', '--workspace', str(root), '--slug', 'fixture', '--job', 'job.txt', '--company', 'Example', '--title', 'Developer']) == 0
    assert (root / 'applications/fixture/job.txt').read_bytes() == original
    capsys.readouterr()
    assert main(['status', '--workspace', str(root), '--application', 'applications/fixture']) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['readiness'] == 'draft_only'
    assert result['release_available'] is False
