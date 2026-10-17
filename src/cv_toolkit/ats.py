"""Generic local extraction checks with no fixed identity or geography."""
from __future__ import annotations

from collections.abc import Mapping
from html.parser import HTMLParser
from pathlib import Path
import re
import unicodedata

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from .render import _safe_href
from .artifact_audit import observe
from .page_layout import observe_page_balance


class _DocumentText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = []
        self.unsafe = False
        self.headings = []
        self.heading = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag in {'script', 'iframe', 'object', 'embed', 'img', 'link', 'form', 'base'}:
            self.unsafe = True
        if any(key.startswith('on') for key in attributes):
            self.unsafe = True
        if tag == 'a' and 'href' in attributes:
            try:
                self.unsafe |= not _safe_href(attributes['href'] or '')
            except ValueError:
                self.unsafe = True
        if tag == 'meta' and (attributes.get('http-equiv') or '').lower() == 'refresh':
            self.unsafe = True
        is_hidden = tag in {'style', 'script', 'head', 'template'} or 'hidden' in attributes
        is_hidden |= bool(re.search(r'(?:display\s*:\s*none|visibility\s*:\s*hidden)', attributes.get('style') or '', re.I))
        if tag not in {'br', 'hr', 'meta', 'link', 'img', 'input', 'base'}:
            self.hidden.append((tag, is_hidden))
        if re.fullmatch(r'h[1-6]', tag) and not any(hidden for _, hidden in self.hidden):
            self.heading = (tag, [])
        self.parts.append('\n')

    def handle_endtag(self, tag):
        if self.heading is not None and self.heading[0] == tag:
            self.headings.append(''.join(self.heading[1]))
            self.heading = None
        for index in range(len(self.hidden) - 1, -1, -1):
            if self.hidden[index][0] == tag:
                del self.hidden[index:]
                break
        self.parts.append('\n')

    def handle_data(self, data):
        if not any(hidden for _, hidden in self.hidden):
            self.parts.append(data)
            if self.heading is not None:
                self.heading[1].append(data)
        elif any(tag == 'style' for tag, _ in self.hidden) and re.search(r'@import|url\s*\(', data, re.I):
            self.unsafe = True

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)


def _normal(value):
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().split())


def _words(text):
    return len(re.findall(r'\b\w+(?:[’\'-]\w+)*\b', text, re.UNICODE))


def _identity(candidate):
    if not isinstance(candidate, Mapping):
        raise ValueError('invalid candidate')
    identity = candidate.get('identity', candidate)
    if not isinstance(identity, Mapping):
        raise ValueError('invalid candidate')
    contact = identity.get('contact', candidate.get('contact', {}))
    if not isinstance(contact, Mapping):
        raise ValueError('invalid candidate')
    merged = dict(contact)
    merged.update(identity)
    return merged


def _check_document(path, candidate, policy, kind):
    issues = []
    text = ''
    pages = None
    headings_in_document = []
    reader = None
    readable = False

    def issue(code, message):
        issues.append({'code': code, 'message': message})

    try:
        path = Path(path)
        if path.suffix.lower() in {'.html', '.htm'}:
            parsed = _DocumentText()
            parsed.feed(path.read_text(encoding='utf-8'))
            text = ''.join(parsed.parts)
            headings_in_document = parsed.headings
            if parsed.unsafe:
                issue('unsafe_html', 'Document contains active markup or embedded assets.')
            readable = True
        elif path.suffix.lower() == '.pdf':
            reader = PdfReader(path)
            pages = len(reader.pages)
            text = '\n'.join(page.extract_text() or '' for page in reader.pages)
            headings_in_document = text.splitlines()
            readable = True
        else:
            issue('unsupported_format', 'Only HTML and PDF documents can be checked.')
    except (OSError, ValueError, PdfReadError, RecursionError, NotImplementedError):
        issue('unreadable_document', 'Document could not be read.')
    if not text.strip():
        issue('empty_text', 'Document has no extractable text.')
    if '\ufffd' in text:
        issue('replacement_character', 'Document contains replacement characters.')
    try:
        identity = _identity(candidate)
        normalized = _normal(text)
        for key, code, message in [('display_name', 'missing_name', 'Expected candidate name was not found.'),
                                   ('email', 'missing_email', 'Expected email was not found.')]:
            expected = identity.get(key, identity.get('name') if key == 'display_name' else None)
            if expected is not None:
                if not isinstance(expected, str) or not expected.strip():
                    raise ValueError('invalid candidate')
                boundary = r'\w' if key == 'display_name' else r'\w.+-'
                if re.search(rf'(?<![{boundary}]){re.escape(_normal(expected))}(?![{boundary}])', normalized) is None:
                    issue(code, message)
        phone = identity.get('phone')
        if phone is not None:
            if not isinstance(phone, str) or not re.search(r'\d', phone):
                raise ValueError('invalid candidate')
            expected_digits = ''.join(re.findall(r'\d', phone))
            extracted_numbers = [
                ''.join(re.findall(r'\d', match.group()))
                for match in re.finditer(r'(?<!\d)\+?\d[\d ().\-\u00a0]{4,}\d(?!\d)', text)
            ]
            if expected_digits not in extracted_numbers:
                issue('missing_phone', 'Expected phone number was not found.')
        pattern = identity.get('phone_pattern')
        if pattern is not None:
            if not isinstance(pattern, str) or not pattern:
                raise ValueError('invalid candidate')
            if re.search(pattern, text) is None:
                issue('missing_phone', 'Expected phone number was not found.')
    except (ValueError, TypeError, re.error, OverflowError, RecursionError):
        issue('invalid_candidate', 'Invalid candidate check configuration.')
    word_count = _words(text)
    try:
        policy = {} if policy is None else policy
        if not isinstance(policy, Mapping):
            raise ValueError('invalid policy')
        max_pages = policy.get('max_letter_pages' if kind == 'cover_letter' else 'max_resume_pages')
        if max_pages is not None:
            if type(max_pages) is not int or max_pages < 1:
                raise ValueError('invalid policy')
            if pages is not None and pages > max_pages:
                issue('page_limit', 'Document exceeds the configured page limit.')
        headings = policy.get('required_headings', [])
        if not isinstance(headings, list) or any(not isinstance(h, str) or not h.strip() for h in headings):
            raise ValueError('invalid policy')
        for heading in headings:
            if _normal(heading) not in {_normal(line) for line in headings_in_document}:
                issue('missing_heading', 'A configured required heading was not found.')
        if kind == 'cover_letter':
            minimum = policy.get('min_letter_words', 0)
            maximum = policy.get('max_letter_words')
            if type(minimum) is not int or minimum < 0 or (maximum is not None and (type(maximum) is not int or maximum < minimum)):
                raise ValueError('invalid policy')
            if word_count < minimum:
                issue('word_count_min', 'Letter has fewer words than the configured minimum.')
            if maximum is not None and word_count > maximum:
                issue('word_count_max', 'Letter has more words than the configured maximum.')
    except (ValueError, TypeError):
        issue('invalid_policy', 'Invalid document check policy.')
    result = {'status': 'fail' if issues else 'pass', 'issues': issues,
            'findings': [item['message'] for item in issues], 'word_count': word_count, 'pages': pages,
            'artifact_audit': observe(text, reader=reader, readable=readable)}
    if kind == 'resume':
        result['layout_audit'] = observe_page_balance(reader)
    return result


def check(doc_path, candidate, policy=None) -> dict:
    """Check extractable identity, text and optional resume constraints locally."""
    return _check_document(doc_path, candidate, policy, 'resume')
