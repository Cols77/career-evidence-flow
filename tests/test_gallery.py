import json
from pathlib import Path

import pytest

from cv_toolkit.cli import main


def test_gallery_text_comparison_accepts_visual_case_and_wrapping_but_not_missing_content():
    from cv_toolkit.gallery import _text_key

    assert _text_key('Professional Experience\nOffice tools') == _text_key('PROFESSIONAL EXPERIENCE\nOfﬁce\ntools')
    assert _text_key('Built 12 tools') != _text_key('Built 2 tools')


def test_showcase_is_installable_validated_and_stays_synthetic(tmp_path, capsys):
    from cv_toolkit.onboarding import classify

    root = tmp_path / 'showcase'
    assert main(['init', str(root), '--example', 'showcase']) == 0
    assert json.loads(capsys.readouterr().out)['synthetic'] is True
    assert main(['validate-evidence', '--workspace', str(root)]) == 0
    capsys.readouterr()
    assert main(['validate-projection', '--workspace', str(root)]) == 0
    capsys.readouterr()
    assert classify(root).state == 'synthetic'
    source = (root / 'resume.md').read_text(encoding='utf-8')
    assert 'fictional' in source.lower()
    assert '### Earlier Experience' in source
    assert '[pagebreak]' in source


def test_gallery_html_renders_every_style_with_identical_content_outside_checkout(tmp_path, capsys, monkeypatch):
    from cv_toolkit.ats import _DocumentText

    monkeypatch.chdir(tmp_path)
    output = tmp_path / 'comparison'
    assert main(['gallery', '--output', str(output), '--format', 'html']) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['synthetic'] is True
    assert result['review_status'] == 'unreviewed_preview'
    report = json.loads((output / 'checks.json').read_text())
    texts = []
    for style in ('ats', 'branded', 'modern', 'minimal'):
        html = (output / f'{style}.html').read_text(encoding='utf-8')
        parsed = _DocumentText()
        parsed.feed(html)
        texts.append(' '.join(''.join(parsed.parts).split()))
        assert not parsed.unsafe
        assert report[style]['html']['status'] == 'pass'
        assert f'{style}.html' in (output / 'index.html').read_text()
    assert len(set(texts)) == 1
    assert '[pagebreak]' not in texts[0]
    assert not list(output.glob('*.pdf'))


def test_gallery_refuses_to_overwrite_existing_output(tmp_path, capsys):
    target = tmp_path / 'existing'
    target.mkdir()
    (target / 'index.html').write_text('Keep me')
    assert main(['gallery', '--output', str(target), '--format', 'html']) == 2
    capsys.readouterr()
    assert (target / 'index.html').read_text() == 'Keep me'


def test_gallery_pdf_failure_does_not_leave_a_partial_gallery(tmp_path, monkeypatch, capsys):
    from cv_toolkit import render

    def fail(*args, **kwargs):
        raise RuntimeError('browser unavailable')

    monkeypatch.setattr(render, 'render_pdf', fail)
    output = tmp_path / 'gallery'
    assert main(['gallery', '--output', str(output), '--format', 'both']) == 2
    capsys.readouterr()
    assert not output.exists()
