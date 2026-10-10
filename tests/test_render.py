from pathlib import Path
import importlib
import subprocess

from pypdf import PdfWriter
import pytest


def renderer():
    return importlib.import_module('cv_toolkit.render')


@pytest.mark.parametrize('style', ['ats', 'branded', 'letter'])
def test_packaged_styles_render_unicode_and_escape_document_title(style):
    html = renderer().render_html('# Zoë & Example\n\nEngineering experience.', style=style)
    assert '<h1>Zoë &amp; Example</h1>' in html
    assert '<title>Zoë &amp; Example</title>' in html
    assert '<style>' in html and '@page' in html
    assert 'Content-Security-Policy' in html


@pytest.mark.parametrize('source', [
    '<script>alert(1)</script>', '<img src="file:///secret">',
    '<link href="https://invalid.example/x.css" rel="stylesheet">',
    '<style>@import "https://invalid.example/x";</style>',
    '<iframe src="file:///secret"></iframe>', '<div onclick="evil()">text</div>',
    '![image](https://invalid.example/x.png)', '![image](file:///secret)',
    '![image](../secret.png)', '![image](data:image/png;base64,AA)',
    '[link](javascript:alert%281%29)', '[link](file:///secret)', '[link](data:text/html,bad)',
])
def test_active_markup_and_asset_references_are_rejected(source):
    with pytest.raises(ValueError, match='unsafe'):
        renderer().render_html(source)


def test_inert_links_and_comparison_text_remain_usable():
    html = renderer().render_html('2 < 3 & 5 > 4\n\n[Portfolio](https://example.invalid)')
    assert '2 &lt; 3' in html
    assert 'href="https://example.invalid"' in html


@pytest.mark.parametrize('kwargs', [{'style': '../secret'}, {'document_kind': 'script'}])
def test_unknown_style_and_kind_are_rejected(kwargs):
    with pytest.raises(ValueError):
        renderer().render_html('# Example', **kwargs)


def fake_pdf(path):
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    with Path(path).open('wb') as target:
        writer.write(target)


def test_each_pdf_invocation_uses_fresh_html_and_isolated_profile(tmp_path, monkeypatch):
    module = renderer()
    source = tmp_path / 'resume.md'
    cached = tmp_path / 'resume.html'
    cached.write_text('<script>stale injection</script>')
    browser = tmp_path / 'chrome.exe'
    browser.touch()
    output = tmp_path / 'exports' / 'resume.pdf'
    seen = []

    def run(command, **kwargs):
        from urllib.parse import urlsplit, unquote
        from urllib.request import url2pathname
        html_path = Path(url2pathname(unquote(urlsplit(command[-1]).path)))
        seen.append((html_path.read_text(encoding='utf-8'), next(x for x in command if x.startswith('--user-data-dir='))))
        target = next(x.split('=', 1)[1] for x in command if x.startswith('--print-to-pdf='))
        assert not output.exists() or output.read_bytes().startswith(b'%PDF-')
        fake_pdf(target)
        return subprocess.CompletedProcess(command, 0, '', '')

    monkeypatch.setattr(module.subprocess, 'run', run)
    source.write_text('# Version One', encoding='utf-8')
    assert module.render_pdf(source, output, chrome_path=browser) == output.resolve()
    source.write_text('# Version Two', encoding='utf-8')
    module.render_pdf(source, output, chrome_path=browser)
    assert 'Version One' in seen[0][0] and 'Version Two' in seen[1][0]
    assert 'stale injection' not in ''.join(x[0] for x in seen)
    assert seen[0][1] != seen[1][1]
    assert cached.read_text() == '<script>stale injection</script>'


def test_browser_failure_preserves_existing_output_without_private_error_text(tmp_path, monkeypatch):
    module = renderer()
    source = tmp_path / 'source.md'
    source.write_text('# Example')
    browser = tmp_path / 'chrome.exe'
    browser.touch()
    output = tmp_path / 'result.pdf'
    output.write_bytes(b'existing output')
    monkeypatch.setattr(module.subprocess, 'run', lambda *a, **k: subprocess.CompletedProcess(a, 1, '', 'private secret'))
    with pytest.raises(RuntimeError) as error:
        module.render_pdf(source, output, chrome_path=browser)
    assert 'private secret' not in str(error.value)
    assert output.read_bytes() == b'existing output'


def test_invalid_pdf_is_not_promoted(tmp_path, monkeypatch):
    module = renderer()
    source = tmp_path / 'source.md'
    source.write_text('# Example')
    browser = tmp_path / 'chrome.exe'
    browser.touch()
    output = tmp_path / 'result.pdf'

    def run(command, **kwargs):
        target = next(x.split('=', 1)[1] for x in command if x.startswith('--print-to-pdf='))
        Path(target).write_text('broken')
        return subprocess.CompletedProcess(command, 0, '', '')

    monkeypatch.setattr(module.subprocess, 'run', run)
    with pytest.raises(RuntimeError):
        module.render_pdf(source, output, chrome_path=browser)
    assert not output.exists()


def test_missing_browser_is_explicit(tmp_path, monkeypatch):
    module = renderer()
    monkeypatch.setattr(module, '_find_chromium', lambda: None)
    source = tmp_path / 'source.md'
    source.write_text('# Example')
    with pytest.raises(RuntimeError, match='Chrome|Chromium'):
        module.render_pdf(source, tmp_path / 'output.pdf')


def test_malformed_pdf_with_magic_header_has_a_sanitized_render_error(tmp_path, monkeypatch):
    module = renderer()
    source = tmp_path / 'source.md'
    source.write_text('# Example')
    browser = tmp_path / 'chrome.exe'
    browser.touch()
    output = tmp_path / 'result.pdf'

    def run(command, **kwargs):
        target = next(x.split('=', 1)[1] for x in command if x.startswith('--print-to-pdf='))
        Path(target).write_bytes(b'%PDF-1.7\nprivate broken output')
        return subprocess.CompletedProcess(command, 0, '', '')

    monkeypatch.setattr(module.subprocess, 'run', run)
    with pytest.raises(RuntimeError, match='Chromium PDF rendering failed'):
        module.render_pdf(source, output, chrome_path=browser)
    assert not output.exists()
