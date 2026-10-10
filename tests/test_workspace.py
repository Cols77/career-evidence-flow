import json
from pathlib import Path

import pytest

from cv_toolkit.workspace import Workspace, WorkspaceError, _safe_export_name


def write_config(root: Path, body: str) -> None:
    (root / "cvtool.toml").write_text(body, encoding="utf-8")


def valid_config() -> str:
    return '''
[profile]
display_name = "Zoë/李"
email = "zoe@example.test"

[paths]
profile = "profile"
applications = "applications"
styles = "styles"
outputs = "outputs"

[ats]
phone_pattern = "^[0-9]+$"
'''


def test_loads_valid_config_without_creating_directories(tmp_path):
    write_config(tmp_path, valid_config())
    workspace = Workspace.load(tmp_path)
    assert workspace.display_name == "Zoë/李"
    assert workspace.export_name == "Zoë_李"
    assert workspace.email == "zoe@example.test"
    assert workspace.phone_pattern == "^[0-9]+$"
    assert not (tmp_path / "profile").exists()


def test_optional_contact_fields_are_absent_not_empty_defaults(tmp_path):
    write_config(tmp_path, valid_config().replace('email = "zoe@example.test"\n', "").replace(
        '[ats]\nphone_pattern = "^[0-9]+$"', "[ats]"
    ))
    workspace = Workspace.load(tmp_path)
    assert workspace.email is None
    assert workspace.phone_pattern is None


def test_malformed_toml_is_sanitized(tmp_path):
    write_config(tmp_path, "[profile\ndisplay_name = 'x'")
    with pytest.raises(WorkspaceError, match="invalid workspace configuration"):
        Workspace.load(tmp_path)


def test_missing_display_name_is_rejected(tmp_path):
    write_config(tmp_path, valid_config().replace('display_name = "Zoë/李"', ""))
    with pytest.raises(WorkspaceError, match="invalid display_name"):
        Workspace.load(tmp_path)


@pytest.mark.parametrize("bad", [
    "../outside", "nested/../outside", "/tmp/outside", "\\\\rooted\\share",
    "C:/outside", "C:\\\\outside", "C:outside",
])
@pytest.mark.parametrize("field", ["profile", "applications", "styles", "outputs"])
def test_portable_unsafe_paths_are_rejected(tmp_path, field, bad):
    body = valid_config().replace(f'{field} = "{field}"', f'{field} = {json.dumps(bad)}')
    write_config(tmp_path, body)
    with pytest.raises(WorkspaceError, match=f"invalid {field} path"):
        Workspace.load(tmp_path)


def test_normal_nested_paths_are_accepted_without_creation(tmp_path):
    body = valid_config().replace('profile = "profile"', 'profile = "nested/profile"')
    write_config(tmp_path, body)
    assert Workspace.load(tmp_path).profile_dir == (tmp_path / "nested" / "profile").resolve()


@pytest.mark.parametrize("raw", [
    "../profile", "nested/../profile", "/root", "\\\\root",
    "C:/root", "C:\\\\root", "C:root", "\\\\server\\share",
])
def test_portable_windows_and_traversal_paths_are_rejected(tmp_path, raw):
    body = valid_config().replace('profile = "profile"', f'profile = {json.dumps(raw)}')
    write_config(tmp_path, body)
    with pytest.raises(WorkspaceError, match="invalid profile path"):
        Workspace.load(tmp_path)


def test_symlink_escape_is_rejected_when_supported(tmp_path):
    outside = tmp_path.parent / "workspace-outside"
    outside.mkdir()
    link = tmp_path / "profile-link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable on this host")
    body = valid_config().replace('profile = "profile"', 'profile = "profile-link"')
    write_config(tmp_path, body)
    with pytest.raises(WorkspaceError, match="invalid profile path"):
        Workspace.load(tmp_path)


def test_symlinked_config_outside_root_is_rejected(tmp_path):
    outside = tmp_path.parent / "config-outside.toml"
    outside.write_text(valid_config(), encoding="utf-8")
    config = tmp_path / "cvtool.toml"
    try:
        config.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable on this host")
    with pytest.raises(WorkspaceError, match="invalid workspace configuration"):
        Workspace.load(tmp_path)


def test_malformed_phone_regex_is_rejected(tmp_path):
    write_config(tmp_path, valid_config().replace("^[0-9]+$", "["))
    with pytest.raises(WorkspaceError, match="invalid phone_pattern"):
        Workspace.load(tmp_path)


@pytest.mark.parametrize("raw,expected", [
    ("__Alex_ ", "_Alex_"),
    ("..Alex..", "..Alex"),
    ("___", "_"),
    ("Zoë/李", "Zoë_李"),
    ("<>:\\/|?*\x00\u0085", "candidate"),
    ("", "invalid export_name"),
    ("   ", "invalid export_name"),
])
def test_export_name_edge_controls_are_deterministic(tmp_path, raw, expected):
    assert _safe_export_name(raw) == ("candidate" if not raw.strip() else expected)
    body = valid_config().replace('display_name = "Zoë/李"', 'display_name = "Alex"')
    body = body.replace('display_name = "Alex"', f'display_name = "Alex"\nexport_name = {json.dumps(raw)}')
    write_config(tmp_path, body)
    if not raw.strip():
        with pytest.raises(WorkspaceError, match=expected):
            Workspace.load(tmp_path)
        return
    assert Workspace.load(tmp_path).export_name == expected


@pytest.mark.parametrize("explicit", [False, True])
@pytest.mark.parametrize("raw,expected", [
    ("  Alex  ", "  Alex"),
    ("__Alex_ ", "_Alex_"),
    ("Zoë/李", "Zoë_李"),
    ("CON", "_CON"),
])
def test_explicit_and_derived_export_names_share_algorithm(tmp_path, explicit, raw, expected):
    replacement = f'display_name = {json.dumps(raw)}'
    if explicit:
        replacement += f'\nexport_name = {json.dumps(raw)}'
    body = valid_config().replace('display_name = "Zoë/李"', replacement)
    write_config(tmp_path, body)
    workspace = Workspace.load(tmp_path)
    assert workspace.display_name == raw.strip()
    assert workspace.export_name == expected


def test_windows_reserved_export_name_is_safe(tmp_path):
    body = valid_config().replace('display_name = "Zoë/李"', 'display_name = "Alex"')
    body = body.replace('display_name = "Alex"', 'display_name = "Alex"\nexport_name = "CON"')
    write_config(tmp_path, body)
    assert Workspace.load(tmp_path).export_name == "_CON"


@pytest.mark.parametrize("pattern", ["x{4294967296}", "(" * 1100 + "x" + ")" * 1100],
                         ids=["overflow", "recursion"])
def test_phone_regex_resource_errors_are_sanitized(tmp_path, pattern):
    write_config(tmp_path, valid_config().replace("^[0-9]+$", pattern))
    with pytest.raises(WorkspaceError) as error:
        Workspace.load(tmp_path)
    assert str(error.value) == "invalid phone_pattern"
    assert error.value.__suppress_context__


@pytest.mark.parametrize("explicit", [False, True])
@pytest.mark.parametrize("raw", [
    "COM¹", "COM²", "COM³", "LPT¹", "LPT²", "LPT³",
    "com¹.txt", "CoM².pdf", "COM³.txt", "lpt¹.txt", "LPT².pdf", "LpT³.txt",
])
def test_superscript_device_export_names_are_writable(tmp_path, explicit, raw):
    replacement = f'display_name = {json.dumps(raw)}'
    if explicit:
        replacement += f'\nexport_name = {json.dumps(raw)}'
    write_config(tmp_path, valid_config().replace('display_name = "Zoë/李"', replacement))
    name = Workspace.load(tmp_path).export_name
    assert name == "_" + raw
    target = tmp_path / name
    target.write_text("synthetic", encoding="utf-8")
    assert target.read_text(encoding="utf-8") == "synthetic"


@pytest.mark.parametrize("raw", ["COM⁴", "LPT₁", "Zoë李", "_COM1"])
def test_ordinary_unicode_export_names_are_preserved(tmp_path, raw):
    write_config(tmp_path, valid_config().replace('display_name = "Zoë/李"',
                                               f'display_name = {json.dumps(raw)}'))
    assert Workspace.load(tmp_path).export_name == raw
