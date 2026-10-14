"""Read-only, sanitized document observations; never an authorship detector."""
from collections import Counter
import unicodedata

from pypdf.errors import PdfReadError


_METADATA_FIELDS = {'/Title', '/Author', '/Subject', '/Keywords', '/Creator',
                    '/Producer', '/CreationDate', '/ModDate', '/Trapped'}


def observe(text, *, reader=None, readable=True):
    """Reuse extracted text and the open PDF reader, without returning values.

    PDF operator counts cover page content streams only. They identify explicit
    non-painting text modes (3 and 7), not actual hidden strings or authorship.
    Forms, clipping, opacity, images and white/off-page text need visual review.
    """
    report = {
        'status': 'observed' if readable else 'unavailable',
        'authorship_detection_performed': False,
        'visual_inspection_performed': False,
        'format_characters': dict(sorted(Counter(
            f'U+{ord(char):04X}' for char in text
            if unicodedata.category(char) == 'Cf').items())),
        'limitations': ['No authorship or statistical watermark detection.',
                        'Extracted text does not establish visibility; inspect rendered pages.'],
    }
    if not readable or reader is None:
        return report
    try:
        metadata = set(reader.metadata or {})
        watermarks = 0
        invisible = 0
        for page in reader.pages:
            for annotation in page.get('/Annots', []):
                if annotation.get_object().get('/Subtype') == '/Watermark':
                    watermarks += 1
            content = page.get_contents()
            if content is not None:
                invisible += sum(operator == b'Tr' and bool(operands)
                                 and operands[0] in (3, 7)
                                 for operands, operator in content.operations)
        report['pdf'] = {
            'metadata_fields': sorted(metadata & _METADATA_FIELDS),
            'other_metadata_field_count': len(metadata - _METADATA_FIELDS),
            'renderer_metadata_present': bool(metadata & {'/Creator', '/Producer'}),
            'xmp_present': '/Metadata' in reader.root_object,
            'attachment_count': sum(1 for _ in reader.attachment_list),
            'watermark_annotation_count': watermarks,
            'invisible_text_rendering_operator_count': invisible,
        }
        report['limitations'].append(
            'PDF indicators cover watermark annotations and page-stream Tr modes 3/7 only; '
            'form streams, opacity, clipping, white/off-page text and image watermarks are not checked.')
    except (OSError, ValueError, TypeError, KeyError, AttributeError,
            PdfReadError, RecursionError, NotImplementedError):
        report['status'] = 'unavailable'
    return report
