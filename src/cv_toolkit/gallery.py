"""Build a self-contained comparison from the packaged fictional resume."""
from html import escape
from importlib.resources import files
import json
import os
from pathlib import Path
import re
import tempfile
import unicodedata

from . import ats, render
from .bootstrap import init_workspace
from .workspace import Workspace


THEMES = (
    ('branded', 'Editorial', 'Warm ivory, bronze accents and serif experience headings.'),
    ('modern', 'Modern', 'White paper, navy type and a clear sans-serif hierarchy.'),
    ('minimal', 'Minimal', 'Monochrome serif typography and restrained rules.'),
    ('ats', 'ATS', 'Plain, single-column text with stacked dates.'),
)


def _text_key(text):
    # CSS uppercase, PDF line wrapping and font ligatures do not change content.
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', text)).replace('\u00ad', '').casefold()


def render_gallery(output: Path, *, include_pdf: bool = False):
    """Publish a complete local demo, refusing existing destinations.

    Failure leaves no partially generated gallery at the requested path.
    Only packaged synthetic content is accepted by this command.
    """
    output = Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise ValueError('gallery destination must be new')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.cv-gallery-', dir=output.parent,
                                     ignore_cleanup_errors=True) as temporary:
        staging = Path(temporary)
        workspace = init_workspace(staging / 'example', example='showcase')
        ws = Workspace.load(workspace)
        identity = {'display_name': ws.display_name, 'email': ws.email}
        source = workspace / 'resume.md'
        markdown_text = source.read_text(encoding='utf-8')
        destination = staging / 'gallery'
        destination.mkdir()
        report, cards = {}, []
        baseline_text = None
        for style, title, description in THEMES:
            html = render.render_html(markdown_text, style=style)
            html_path = destination / f'{style}.html'
            html_path.write_text(html, encoding='utf-8')
            check = ats.check(html_path, identity, {'max_resume_pages': 2})
            parsed = ats._DocumentText()
            parsed.feed(html)
            text = _text_key(''.join(parsed.parts))
            if baseline_text is None:
                baseline_text = text
            if check['status'] != 'pass' or text != baseline_text:
                raise RuntimeError('gallery HTML verification failed')
            report[style] = {'html': check, 'same_content': True}
            links = f'<a href="{style}.html">Open HTML</a>'
            if include_pdf:
                pdf_path = destination / f'{style}.pdf'
                render.render_pdf(source, pdf_path, style=style)
                pdf_check = ats.check(pdf_path, identity, {'max_resume_pages': 2})
                extracted = '\n'.join(page.extract_text() or '' for page in render.PdfReader(pdf_path).pages)
                matches = _text_key(extracted) == text
                report[style].update(pdf=pdf_check, pdf_matches_html=matches)
                if pdf_check['status'] != 'pass' or not matches:
                    raise RuntimeError('gallery PDF verification failed')
                links += f' <a href="{style}.pdf">Open PDF</a>'
            cards.append(
                f'<section id="{style}"><h2>{escape(title)}</h2>'
                f'<p>{escape(description)}</p><p class="links">{links}</p>'
                f'<iframe title="{escape(title)} fictional resume" src="{style}.html" loading="lazy"></iframe>'
                '</section>'
            )
        template = files('cv_toolkit').joinpath('assets', 'gallery.html').read_text(encoding='utf-8')
        (destination / 'index.html').write_text(template.replace('<!-- cards -->', '\n'.join(cards)), encoding='utf-8')
        (destination / 'checks.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        (destination / 'resume.md').write_text(markdown_text, encoding='utf-8')
        # A second check protects destinations created while rendering.
        if output.exists() or output.is_symlink():
            raise ValueError('gallery destination already exists')
        os.rename(destination, output)
    return {'synthetic': True, 'styles': [row[0] for row in THEMES],
            'review_status': 'unreviewed_preview', 'format': 'both' if include_pdf else 'html'}
