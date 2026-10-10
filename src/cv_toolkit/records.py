"""Strict local records, confined paths and atomic JSON persistence."""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import re
import tempfile

MAX_RECORD_BYTES = 2_000_000
MAX_DEPTH = 64
MAX_INTEGER_DIGITS = 1000
ID_PATTERN = re.compile(r'[a-z0-9][a-z0-9._-]+')
SOURCE_ID_PATTERN = re.compile(r'source\.[a-z0-9][a-z0-9._-]+')
_RESERVED = {'CON', 'PRN', 'AUX', 'NUL', *(f'{p}{n}' for p in ('COM', 'LPT') for n in '123456789¹²³')}


class ToolkitError(ValueError):
    """A local validation failure containing rule names, never supplied values."""


def nonempty(value, rule):
    if not isinstance(value, str) or not value.strip():
        raise ToolkitError(f'invalid {rule}')
    try:
        value.encode('utf-8')
    except UnicodeError:
        raise ToolkitError(f'invalid {rule}') from None
    return value


def identifier(value, rule='identifier', *, source=False):
    pattern = SOURCE_ID_PATTERN if source else ID_PATTERN
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ToolkitError(f'invalid {rule}')
    return value


def object_fields(value, required, optional=(), *, rule='record'):
    if not isinstance(value, dict) or not set(required) <= value.keys() or value.keys() - set(required) - set(optional):
        raise ToolkitError(f'invalid {rule} fields')
    return value


def schema(value):
    if type(value) is not int or value != 1:
        raise ToolkitError('unsupported schema_version')


def identifiers(value, rule, *, nonempty_list=False):
    if not isinstance(value, list) or (nonempty_list and not value):
        raise ToolkitError(f'invalid {rule}')
    seen = set()
    for entry in value:
        identifier(entry, rule)
        if entry in seen:
            raise ToolkitError(f'duplicate {rule}')
        seen.add(entry)
    return value


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ToolkitError('duplicate JSON key')
        result[key] = value
    return result


def _constant(value):
    raise ToolkitError('invalid JSON constant')


def _integer(value):
    if len(value.lstrip('-')) > MAX_INTEGER_DIGITS:
        raise ToolkitError('JSON integer exceeds limit')
    return int(value)


def _validate_json(value, depth=0):
    if depth > MAX_DEPTH:
        raise ToolkitError('JSON nesting exceeds limit')
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ToolkitError('invalid JSON key')
            _validate_json(key, depth + 1)
            _validate_json(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            _validate_json(child, depth + 1)
    elif isinstance(value, str):
        value.encode('utf-8')
    elif type(value) is float and not math.isfinite(value):
        raise ToolkitError('invalid JSON number')
    elif type(value) is int and len(str(abs(value))) > MAX_INTEGER_DIGITS:
        raise ToolkitError('JSON integer exceeds limit')
    elif value is not None and type(value) not in (int, float, bool):
        raise ToolkitError('invalid JSON value')


def _decode(raw):
    if len(raw) > MAX_RECORD_BYTES:
        raise ToolkitError('JSON record exceeds limit')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs, parse_constant=_constant, parse_int=_integer)
        _validate_json(value)
        return value
    except ToolkitError:
        raise
    except (ValueError, UnicodeError, RecursionError, OverflowError):
        raise ToolkitError('invalid JSON record') from None


def load_json(path: Path):
    try:
        with Path(path).open('rb') as stream:
            raw = stream.read(MAX_RECORD_BYTES + 1)
    except (OSError, ValueError):
        raise ToolkitError('unreadable JSON record') from None
    return _decode(raw)


def confined(root, raw, required=True):
    nonempty(raw, 'relative path')
    lexical = raw.replace('\\', '/')
    parts = lexical.split('/')
    if any(part in ('', '.', '..') or re.search(r'[<>:"|?*\x00-\x1f]', part) or part.endswith((' ', '.')) or part.split('.')[0].upper() in _RESERVED for part in parts):
        raise ToolkitError('invalid relative path')
    try:
        base = Path(root).resolve(strict=True)
        if not base.is_dir():
            raise ToolkitError('invalid path root')
        result = base.joinpath(*parts).resolve(strict=required)
        result.relative_to(base)
        return result
    except (OSError, ValueError, RuntimeError):
        raise ToolkitError('path escapes root or is unavailable') from None


def atomic_write_json(path: Path, value):
    """Validate and serialize before creating any temporary file."""
    try:
        _validate_json(value)
        raw = (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode('utf-8')
        _decode(raw)
    except ToolkitError:
        raise
    except (TypeError, ValueError, UnicodeError, RecursionError, OverflowError):
        raise ToolkitError('invalid JSON record') from None
    temporary = None
    try:
        path = Path(path)
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.record-', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except (OSError, ValueError):
        raise ToolkitError('cannot write JSON record') from None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
