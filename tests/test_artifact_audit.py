"""Local artifact observations must be useful without exposing private content."""
import json

import pytest
from pypdf import PdfWriter
from pypdf.generic import (
    ArrayObject, DecodedStreamObject, DictionaryObject, FloatObject,
    NameObject,
)

from cv_toolkit import ats, letter_check


def pdf_fixture(path, *, indicators=False):
    writer = PdfWriter()
    page = writer.add_blank_page(width=595, height=842)
    font = DictionaryObject({NameObject('/Type'): NameObject('/Font'),
                             NameObject('/Subtype'): NameObject('/Type1'),
                             NameObject('/BaseFont'): NameObject('/Helvetica')})
    page[NameObject('/Resources')] = DictionaryObject({
        NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
    stream = DecodedStreamObject()
    stream.set_data(b'BT /F1 12 Tf 20 800 Td (Example Person) Tj ET' +
                    (b' BT /F1 12 Tf 3 Tr ( Secret text) Tj ET' if indicators else b''))
    page[NameObject('/Contents')] = writer._add_object(stream)
    writer.add_metadata({'/Title': 'PRIVATE TITLE', '/Creator': 'HeadlessChrome',
                         '/Producer': 'Skia/PDF'})
    if indicators:
        writer.add_attachment('PRIVATE ATTACHMENT', b'PRIVATE CONTENT')
        metadata = DecodedStreamObject()
        metadata.set_data(b'<private>PRIVATE XMP</private>')
        metadata[NameObject('/Type')] = NameObject('/Metadata')
        metadata[NameObject('/Subtype')] = NameObject('/XML')
        writer._root_object[NameObject('/Metadata')] = writer._add_object(metadata)
        annotation = DictionaryObject({
            NameObject('/Type'): NameObject('/Annot'),
            NameObject('/Subtype'): NameObject('/Watermark'),
            NameObject('/Rect'): ArrayObject([FloatObject(0)] * 4),
        })
        page[NameObject('/Annots')] = ArrayObject([writer._add_object(annotation)])
    writer.write(path)


@pytest.mark.parametrize('checker', [ats.check, letter_check.check])
def test_pdf_audit_reports_observations_without_text_or_metadata_values(tmp_path, checker):
    path = tmp_path / 'document.pdf'
    pdf_fixture(path, indicators=True)
    before = path.read_bytes()
    result = checker(path, {'name': 'Example Person'})
    audit = result['artifact_audit']
    assert audit['status'] == 'observed'
    assert audit['pdf']['metadata_fields'] == ['/Creator', '/Producer', '/Title']
    assert audit['pdf']['xmp_present'] is True
    assert audit['pdf']['attachment_count'] == 1
    assert audit['pdf']['watermark_annotation_count'] == 1
    assert audit['pdf']['invisible_text_rendering_operator_count'] == 1
    assert audit['authorship_detection_performed'] is False
    assert audit['visual_inspection_performed'] is False
    assert result['status'] == 'pass'  # Indicators require review, not automatic rejection.
    assert path.read_bytes() == before
    assert all(value not in json.dumps(result) for value in
               ('PRIVATE', 'Secret text', 'Example Person', str(tmp_path)))


def test_ordinary_renderer_metadata_is_not_an_authorship_finding(tmp_path):
    path = tmp_path / 'document.pdf'
    pdf_fixture(path)
    result = ats.check(path, {})
    assert result['status'] == 'pass'
    assert result['artifact_audit']['pdf']['renderer_metadata_present'] is True
    assert result['artifact_audit']['pdf']['watermark_annotation_count'] == 0
    assert result['artifact_audit']['pdf']['invisible_text_rendering_operator_count'] == 0
    assert result['artifact_audit']['pdf']['attachment_count'] == 0


def test_format_characters_are_reported_without_rewriting_legitimate_text(tmp_path):
    path = tmp_path / 'document.html'
    path.write_text('<p>Example\u200b Person\u200c</p>', encoding='utf-8')
    before = path.read_bytes()
    result = ats.check(path, {})
    assert result['artifact_audit']['format_characters'] == {'U+200B': 1, 'U+200C': 1}
    assert result['status'] == 'pass'
    assert path.read_bytes() == before


def test_unreadable_pdf_cannot_report_a_clean_audit(tmp_path):
    path = tmp_path / 'document.pdf'
    path.write_bytes(b'PRIVATE INVALID PDF')
    result = ats.check(path, {})
    assert result['status'] == 'fail'
    assert result['artifact_audit']['status'] == 'unavailable'
    assert 'PRIVATE' not in json.dumps(result)


def test_duplicate_attachment_names_count_as_separate_files(tmp_path):
    path = tmp_path / 'document.pdf'
    pdf_fixture(path)
    writer = PdfWriter(clone_from=path)
    writer.add_attachment('same.txt', b'first private attachment')
    writer.add_attachment('same.txt', b'second private attachment')
    writer.write(path)
    result = ats.check(path, {})
    assert result['artifact_audit']['pdf']['attachment_count'] == 2
    assert 'private attachment' not in json.dumps(result)
