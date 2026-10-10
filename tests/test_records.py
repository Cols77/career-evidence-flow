import json
from pathlib import Path

import pytest

from cv_toolkit.records import ToolkitError, atomic_write_json, confined, load_json


@pytest.mark.parametrize('raw', [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}', b'\xff', b'[' * 1100 + b'0' + b']' * 1100, b'1' * 5000, b'{"x":"\\ud800"}'])
def test_strict_json_rejects_invalid_data(tmp_path, raw):
    path = tmp_path / 'data.json'
    path.write_bytes(raw)
    with pytest.raises(ToolkitError) as exc:
        load_json(path)
    assert 'data.json' not in str(exc.value)


@pytest.mark.parametrize('raw', ['../secret', '/secret', 'C:\\secret', '\\\\server\\share', 'a/../b', 'file:stream', 'COM¹.txt'])
def test_confined_rejects_portable_unsafe_paths(tmp_path, raw):
    with pytest.raises(ToolkitError):
        confined(tmp_path, raw, required=False)


def test_confined_supports_new_paths_and_rejects_symlink_escape(tmp_path):
    assert confined(tmp_path, 'folder/file.json', required=False) == tmp_path / 'folder' / 'file.json'
    with pytest.raises(ToolkitError):
        confined(tmp_path, 'missing')
    outside = tmp_path.parent / (tmp_path.name + '-outside')
    outside.mkdir()
    try:
        (tmp_path / 'link').symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip('host cannot create symlinks')
    with pytest.raises(ToolkitError):
        confined(tmp_path, 'link/record.json', required=False)


def test_atomic_invalid_value_preserves_original(tmp_path):
    path = tmp_path / 'record.json'
    atomic_write_json(path, {'text': 'café'})
    original = path.read_bytes()
    with pytest.raises(ToolkitError):
        atomic_write_json(path, {'value': float('nan')})
    assert path.read_bytes() == original
    assert sorted(p.name for p in tmp_path.iterdir()) == ['record.json']
