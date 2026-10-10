import importlib
from pypdf import PdfWriter


def checker():
    return importlib.import_module('cv_toolkit.letter_check')


def test_letter_accepts_configured_word_range_without_resume_headings(tmp_path):
    path = tmp_path / 'letter.html'
    path.write_text('<h1>Example Person</h1><p>Hello team. I build reliable software. Regards.</p>')
    result = checker().check(path, {'name': 'Example Person'}, {'min_letter_words': 5, 'max_letter_words': 30})
    assert result['status'] == 'pass'
    assert result['word_count'] == 9


def test_letter_word_limits_and_optional_heading_policy(tmp_path):
    path = tmp_path / 'letter.html'
    path.write_text('<p>Example Person. Hello team.</p>')
    result = checker().check(path, {'name': 'Example Person'}, {'min_letter_words': 20, 'required_headings': ['Motivation']})
    assert {'word_count_min', 'missing_heading'} <= {i['code'] for i in result['issues']}
    result = checker().check(path, {}, {'max_letter_words': 2})
    assert 'word_count_max' in {i['code'] for i in result['issues']}


def test_letter_page_limit_is_independent_of_resume_limit(tmp_path):
    path = tmp_path / 'letter.pdf'
    writer = PdfWriter()
    for _ in range(2):
        writer.add_blank_page(width=595, height=842)
    with path.open('wb') as target:
        writer.write(target)
    result = checker().check(path, {}, {'max_letter_pages': 1, 'max_resume_pages': 9})
    assert result['pages'] == 2
    assert 'page_limit' in {i['code'] for i in result['issues']}


def test_invalid_letter_policy_is_a_sanitized_issue(tmp_path):
    path = tmp_path / 'letter.html'
    path.write_text('Example')
    result = checker().check(path, {}, {'min_letter_words': 30, 'max_letter_words': 10})
    assert 'invalid_policy' in {i['code'] for i in result['issues']}
