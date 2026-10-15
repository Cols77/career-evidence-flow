"""Render untrusted Markdown using packaged, offline document assets."""
from __future__ import annotations

from html import escape
from html.parser import HTMLParser
from importlib import resources
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from urllib.parse import urlsplit

import markdown
from pypdf import PdfReader
from pypdf.errors import PdfReadError


RESUME_STYLES = ('ats', 'branded', 'modern', 'minimal')
STYLES = (*RESUME_STYLES, 'letter')
DOCUMENT_KINDS = ('resume', 'cover_letter')
_RAW_HTML = re.compile(r'<!--|<!|</?[A-Za-z][\w:-]*(?=[\s/>])')
_TAGS = {'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'li', 'strong', 'em',
         'blockquote', 'pre', 'code', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'a', 'br', 'hr'}


def _safe_href(value: str) -> bool:
    if any(ord(char) < 32 for char in value):
        return False
    return value.startswith('#') or urlsplit(value).scheme.lower() in {'http', 'https', 'mailto'}


class _MarkupValidator(HTMLParser):
    def handle_starttag(self, tag, attrs):
        if tag == 'div' and (attrs == [('class', 'entry-head')]
                             or dict(attrs) == {'class': 'page-break', 'aria-hidden': 'true'}):
            return
        if tag not in _TAGS:
            raise ValueError('unsafe document markup')
        for key, value in attrs:
            if tag == 'a' and key == 'href' and value is not None and _safe_href(value):
                continue
            if tag == 'a' and key == 'title':
                continue
            if tag == 'code' and key == 'class' and value and re.fullmatch(r'language-[\w-]+', value):
                continue
            if tag in {'th', 'td'} and key == 'style' and value and re.fullmatch(r'text-align: (left|right|center);', value):
                continue
            raise ValueError('unsafe document markup')

    handle_startendtag = handle_starttag


def render_html(markdown_text: str, style: str = 'ats', document_kind: str = 'resume') -> str:
    """Return safe standalone HTML; HTML markup and embedded assets are rejected.

    Ordinary HTTP(S), mailto and fragment hyperlinks are inert during rendering.
    Styles are package resource names, never caller-provided filesystem paths.
    """
    if style not in STYLES or document_kind not in DOCUMENT_KINDS:
        raise ValueError('invalid document style or kind')
    if not isinstance(markdown_text, str):
        raise ValueError('invalid Markdown input')
    if _RAW_HTML.search(markdown_text):
        raise ValueError('unsafe document markup')
    extensions = ['fenced_code', 'tables', 'sane_lists']
    if document_kind == 'resume':
        from .resume_layout import ResumeLayoutExtension
        extensions.append(ResumeLayoutExtension())
    content = markdown.markdown(markdown_text, extensions=extensions, output_format='html5')
    _MarkupValidator(convert_charrefs=True).feed(content)
    heading = re.search(r'^#\s+(.+?)\s*#*\s*$', markdown_text, re.MULTILINE)
    title = heading.group(1) if heading else ('Cover letter' if document_kind == 'cover_letter' else 'Resume')
    assets = resources.files('cv_toolkit').joinpath('assets')
    template = assets.joinpath('template.html').read_text(encoding='utf-8')
    css = assets.joinpath(f'{style}.css').read_text(encoding='utf-8')
    if style in {'branded', 'modern', 'minimal'}:
        css = assets.joinpath('resume-layout.css').read_text(encoding='utf-8') + '\n' + css
    return template.format(title=escape(title, quote=True), css=css, content=content, document_kind=document_kind)


def _find_chromium() -> Path | None:
    configured = os.environ.get('CV_CHROME_PATH')
    if configured:
        path = Path(configured).expanduser().resolve()
        if path.is_file():
            return path
    if os.name == 'nt':
        for base in (os.environ.get('PROGRAMFILES', 'C:/Program Files'), os.environ.get('PROGRAMFILES(X86)', 'C:/Program Files (x86)')):
            for relative in ('Google/Chrome/Application/chrome.exe', 'Microsoft/Edge/Application/msedge.exe'):
                path = Path(base) / relative
                if path.is_file():
                    return path
    for executable in ('google-chrome', 'chromium', 'chromium-browser', 'chrome', 'msedge'):
        found = shutil.which(executable)
        if found:
            return Path(found).resolve()
    return None


def render_pdf(markdown_path: Path, output_path: Path, style: str = 'ats',
               document_kind: str = 'resume', chrome_path: Path | None = None) -> Path:
    """Regenerate HTML, render in isolation, then atomically replace the PDF.

    An adjacent cached HTML file is never read. Browser diagnostics are not
    surfaced because they may contain private document text or filesystem paths.
    """
    source = Path(markdown_path).resolve(strict=True)
    output = Path(output_path).resolve()
    if output == source:
        raise ValueError('output must differ from Markdown source')
    html = render_html(source.read_text(encoding='utf-8'), style, document_kind)
    browser = Path(chrome_path).resolve() if chrome_path is not None else _find_chromium()
    if browser is None or not browser.is_file():
        raise RuntimeError('Chrome/Chromium is required for PDF rendering')
    ancestor = output.parent
    while not ancestor.exists():
        ancestor = ancestor.parent
    if not ancestor.is_dir() or (output.exists() and not output.is_file()):
        raise ValueError('invalid PDF output path')
    with tempfile.TemporaryDirectory(prefix='cv-render-', dir=ancestor, ignore_cleanup_errors=True) as temporary:
        staging = Path(temporary)
        html_path = staging / 'document.html'
        pdf_path = staging / 'document.pdf'
        html_path.write_text(html, encoding='utf-8')
        command = [str(browser), '--headless=new', '--disable-gpu', '--disable-extensions',
                   '--disable-background-networking', '--disable-component-update', '--no-first-run',
                   '--no-default-browser-check', '--no-pdf-header-footer',
                   '--host-resolver-rules=MAP * ~NOTFOUND', f'--user-data-dir={staging / "profile"}',
                   f'--print-to-pdf={pdf_path}', html_path.as_uri()]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
            if result.returncode != 0 or not pdf_path.is_file() or pdf_path.stat().st_size == 0:
                raise RuntimeError('invalid browser output')
            if not pdf_path.read_bytes().startswith(b'%PDF-') or not PdfReader(pdf_path).pages:
                raise RuntimeError('invalid PDF output')
        except (OSError, subprocess.TimeoutExpired, ValueError, RuntimeError, PdfReadError):
            raise RuntimeError('Chromium PDF rendering failed') from None
        output.parent.mkdir(parents=True, exist_ok=True)
        os.replace(pdf_path, output)
    return output
