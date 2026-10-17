"""Conservative PDF text-extent observations for independent layout review."""
import math

from pypdf.errors import PdfReadError


def observe_page_balance(reader):
    """Flag suspicious pagination without claiming visual inspection or approval.

    Use the toolkit's 14 mm print margin as a reference, not a universal PDF
    constraint. Footer text, images, clipping and unusual transforms can make
    text extents misleading; reviewers must inspect and resolve observations.
    """
    report = {
        'status': 'unavailable', 'visual_inspection_performed': False,
        'pages': [], 'findings': [],
        'limitations': [
            'Text extents estimate vertical use, not painted area or visual quality.',
            'Uses a 14 mm reference margin; footers, graphics, clipping and unusual transforms need visual review.',
            'A review signal is not automatic document rejection; inspect exact rendered pages.',
        ],
    }
    if reader is None:
        return report
    margin = 14 * 72 / 25.4
    try:
        for index, page in enumerate(reader.pages):
            if page.rotation or float(page.get('/UserUnit', 1)) != 1:
                return report
            lower = float(page.cropbox.bottom)
            height = float(page.cropbox.height)
            usable = height - 2 * margin
            if not math.isfinite(usable) or usable <= 0:
                return report
            positions = []

            def visit(text, cm, tm, font, size):
                if not text.strip():
                    return
                y = float(tm[4] * cm[1] + tm[5] * cm[3] + cm[5]) - lower
                scale = math.hypot(tm[2] * cm[0] + tm[3] * cm[2],
                                   tm[2] * cm[1] + tm[3] * cm[3])
                font_height = abs(float(size) * scale)
                if math.isfinite(y) and math.isfinite(font_height) and 0 <= y <= height:
                    positions.append((max(0, y - font_height * .25), min(height, y + font_height)))

            page.extract_text(visitor_text=visit)
            if not positions:
                return report
            bottom = min(p[0] for p in positions)
            top = max(p[1] for p in positions)
            gap = max(0, bottom - margin)
            used = max(0, min(top, height - margin) - max(bottom, margin)) / usable
            report['pages'].append({
                'page': index + 1, 'height_pt': round(height, 2),
                'bottom_gap_pt': round(gap, 2), 'bottom_gap_ratio': round(gap / usable, 4),
                'text_extent_ratio': round(used, 4),
            })
        if not report['pages']:
            return report
        for current, following in zip(report['pages'], report['pages'][1:]):
            if (current['bottom_gap_ratio'] >= .18
                    and current['bottom_gap_ratio'] - following['bottom_gap_ratio'] >= .10):
                report['findings'].append({'code': 'uneven_page_fill', 'page': current['page'],
                                           'message': 'Substantial unused bottom space before a fuller following page; review the page break.'})
        if len(report['pages']) > 1:
            last, previous = report['pages'][-1], report['pages'][-2]
            if last['text_extent_ratio'] < .50 and previous['text_extent_ratio'] >= .80:
                report['findings'].append({'code': 'sparse_final_page', 'page': last['page'],
                                           'message': 'Sparse final page after a full page; review content distribution.'})
        report['status'] = 'review_needed' if report['findings'] else 'observed'
    except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError,
            OverflowError, PdfReadError, RecursionError, NotImplementedError):
        report['status'] = 'unavailable'
    return report
