import importlib
import json

import pytest
from pypdf import PdfWriter


CANDIDATE = {'identity': {'display_name': 'Zoë Example', 'email': 'zoe@example.invalid', 'phone': '+33 6 12 34 56 78'}}


def checker():
    return importlib.import_module('cv_toolkit.ats')


def document(tmp_path, text):
    path = tmp_path / 'resume.html'
    path.write_text('<html><body>' + text + '</body></html>', encoding='utf-8')
    return path


def test_unicode_identity_and_international_phone_have_no_fixed_headings(tmp_path):
    path = document(tmp_path, '<h1>Zoë Example</h1><p>zoe@example.invalid | +33 (6) 12-34-56-78</p><h2>Parcours</h2><p>Engineering work.</p>')
    result = checker().check(path, CANDIDATE)
    assert result['status'] == 'pass' and result['issues'] == []
    assert result['word_count'] > 0 and result['pages'] is None
    assert 'zoe@example.invalid' not in json.dumps(result)


def test_expected_missing_identity_and_contact_are_reported_without_values(tmp_path):
    result = checker().check(document(tmp_path, 'Engineering work'), CANDIDATE)
    assert {'missing_name', 'missing_email', 'missing_phone'} <= {i['code'] for i in result['issues']}
    assert result['status'] == 'fail'
    assert 'Zoë' not in json.dumps(result)


def test_contact_prefixes_and_unrelated_numbers_do_not_satisfy_identity(tmp_path):
    path = document(tmp_path, '<h1>Zoë Exampleton</h1><p>zoe@example.invalid.attacker</p><p>33 years</p><p>6 projects</p><p>12 teams</p><p>34 tests</p><p>56 builds</p><p>78 users</p>')
    result = checker().check(path, CANDIDATE)
    assert {'missing_name', 'missing_email', 'missing_phone'} <= {i['code'] for i in result['issues']}


def test_optional_contacts_and_headings_are_not_invented(tmp_path):
    result = checker().check(document(tmp_path, '<h1>Example Person</h1>Experience'), {'name': 'Example Person'})
    assert result['status'] == 'pass'


def test_workspace_phone_pattern_and_display_name_are_supported(tmp_path):
    path = document(tmp_path, '<h1>Example Person</h1><p>+81 90 1234 5678</p>')
    candidate = {'display_name': 'Example Person', 'phone_pattern': r'\+81\s+90\s+\d{4}\s+\d{4}'}
    assert checker().check(path, candidate)['status'] == 'pass'
    result = checker().check(document(tmp_path, '<h1>Example Person</h1>'), candidate)
    assert 'missing_phone' in {issue['code'] for issue in result['issues']}


def test_policy_required_headings_are_checked_when_configured(tmp_path):
    result = checker().check(document(tmp_path, '<h1>Example Person</h1>Other'), {'name': 'Example Person'}, {'required_headings': ['Experience']})
    assert 'missing_heading' in {i['code'] for i in result['issues']}


def test_body_mentions_do_not_satisfy_required_heading(tmp_path):
    result = checker().check(document(tmp_path, '<h1>Example Person</h1><p>I have Experience designing tools.</p>'), {'name': 'Example Person'}, {'required_headings': ['Experience']})
    assert 'missing_heading' in {i['code'] for i in result['issues']}


@pytest.mark.parametrize('text,code', [('<script>Example Person</script>', 'unsafe_html'), ('<style>Example Person</style>', 'missing_name'), ('<p>Example Person �</p>', 'replacement_character')])
def test_hidden_or_unsafe_text_cannot_satisfy_candidate_checks(tmp_path, text, code):
    result = checker().check(document(tmp_path, text), {'name': 'Example Person'})
    assert code in {i['code'] for i in result['issues']}


def test_pdf_page_limit_is_optional_and_generic(tmp_path):
    path = tmp_path / 'resume.pdf'
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    writer.add_blank_page(width=595, height=842)
    with path.open('wb') as output:
        writer.write(output)
    assert 'page_limit' not in {i['code'] for i in checker().check(path, {}, {})['issues']}
    result = checker().check(path, {}, {'max_resume_pages': 1})
    assert result['pages'] == 2
    assert 'page_limit' in {i['code'] for i in result['issues']}


@pytest.mark.parametrize('filename,contents', [('missing.pdf', None), ('broken.pdf', b'private broken'), ('source.md', b'Example')])
def test_unreadable_and_unsupported_documents_return_sanitized_findings(tmp_path, filename, contents):
    path = tmp_path / filename
    if contents is not None:
        path.write_bytes(contents)
    result = checker().check(path, {})
    assert result['status'] == 'fail'
    assert 'private' not in json.dumps(result) and str(tmp_path) not in json.dumps(result)
