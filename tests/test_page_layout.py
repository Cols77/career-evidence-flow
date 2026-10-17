"""Page balance observations exercise positioned PDF text, not prose matching."""
import json

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject, NumberObject, RectangleObject

from cv_toolkit import ats


def document(path, bottoms, *, rotate=False, scale=1, offset=0, user_unit=1):
    writer = PdfWriter()
    for bottom in bottoms:
        page = writer.add_blank_page(width=595, height=842 + offset)
        page.cropbox = RectangleObject([0, offset, 595, 842 + offset])
        page[NameObject('/UserUnit')] = NumberObject(user_unit)
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
                                 NameObject('/Subtype'): NameObject('/Type1'),
                                 NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
        stream = DecodedStreamObject()
        stream.set_data(f'q {scale} 0 0 {scale} 0 {offset} cm BT /F1 {12/scale} Tf {40/scale} {790/scale} Td (PRIVATE HEADER) Tj ET BT /F1 {12/scale} Tf {40/scale} {bottom/scale} Td (PRIVATE LAST LINE) Tj ET Q'.encode())
        page[NameObject('/Contents')] = writer._add_object(stream)
        if rotate:
            page.rotate(90)
    writer.write(path)
    return path


def test_underfilled_nonfinal_page_is_reported_even_when_two_pages_pass(tmp_path):
    path = document(tmp_path / 'resume.pdf', [250, 70])
    before = path.read_bytes()
    result = ats.check(path, {}, {'max_resume_pages': 2})
    assert result['status'] == 'pass'  # Geometry requests review; it cannot prove a visual defect.
    layout = result['layout_audit']
    assert layout['status'] == 'review_needed'
    assert layout['findings'][0]['code'] == 'uneven_page_fill'
    assert layout['findings'][0]['page'] == 1
    assert layout['pages'][0]['bottom_gap_ratio'] > layout['pages'][1]['bottom_gap_ratio']
    assert path.read_bytes() == before
    assert 'PRIVATE' not in json.dumps(result)


def test_balanced_pages_and_ordinary_final_page_margin_are_not_flagged(tmp_path):
    result = ats.check(document(tmp_path / 'balanced.pdf', [100, 130]), {})
    assert result['layout_audit']['status'] == 'observed'
    assert result['layout_audit']['findings'] == []


def test_sparse_last_page_is_a_separate_review_signal(tmp_path):
    result = ats.check(document(tmp_path / 'sparse.pdf', [60, 550]), {})
    assert result['layout_audit']['status'] == 'review_needed'
    assert result['layout_audit']['findings'][0]['code'] == 'sparse_final_page'
    assert result['layout_audit']['findings'][0]['page'] == 2


def test_rotated_or_blank_pages_do_not_claim_reliable_geometry(tmp_path):
    rotated = ats.check(document(tmp_path / 'rotated.pdf', [250, 70], rotate=True), {})
    assert rotated['layout_audit']['status'] == 'unavailable'
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    blank = tmp_path / 'blank.pdf'
    writer.write(blank)
    assert ats.check(blank, {})['layout_audit']['status'] == 'unavailable'


def test_html_does_not_claim_print_geometry(tmp_path):
    path = tmp_path / 'resume.html'
    path.write_text('<h1>Example Person</h1>', encoding='utf-8')
    assert ats.check(path, {})['layout_audit']['status'] == 'unavailable'


def test_scale_and_shifted_cropbox_preserve_physical_text_extent(tmp_path):
    ordinary = ats.check(document(tmp_path / 'ordinary.pdf', [250, 70]), {})['layout_audit']
    transformed = ats.check(document(tmp_path / 'transformed.pdf', [250, 70], scale=.5, offset=100), {})['layout_audit']
    assert transformed['status'] == ordinary['status'] == 'review_needed'
    assert transformed['pages'] == ordinary['pages']


def test_nondefault_user_unit_does_not_claim_known_reference_geometry(tmp_path):
    result = ats.check(document(tmp_path / 'unit.pdf', [250, 70], user_unit=2), {})
    assert result['layout_audit']['status'] == 'unavailable'
