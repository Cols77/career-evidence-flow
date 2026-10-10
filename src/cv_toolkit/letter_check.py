"""Cover-letter extraction and policy checks using generic identity fields."""
from __future__ import annotations

from .ats import _check_document


def check(path, candidate, policy=None) -> dict:
    """Report identity, page and configured word/heading issues without text."""
    return _check_document(path, candidate, policy, 'cover_letter')
