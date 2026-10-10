from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path
import tomllib
import unicodedata


class WorkspaceError(ValueError):
    """A safe, deterministic workspace configuration failure."""


_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
    *(f"{device}{digit}" for device in ("COM", "LPT") for digit in "¹²³"),
}
_INVALID_FILENAME = re.compile(r'[<>:"/\\|?*]')
_MULTIPLE_UNDERSCORES = re.compile(r"_+")


def _nonempty_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkspaceError(f"invalid {field}")
    return value.strip()


def _safe_export_name(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value)
    safe = "".join(
        "_" if _INVALID_FILENAME.fullmatch(char) or unicodedata.category(char) == "Cc" else char
        for char in normalized
    )
    if not any(
        _INVALID_FILENAME.fullmatch(char) is None and unicodedata.category(char) != "Cc"
        for char in normalized
    ):
        return "candidate"
    normalized = _MULTIPLE_UNDERSCORES.sub("_", safe)
    normalized = normalized.rstrip(" .") or "candidate"
    if normalized.split(".", 1)[0].upper() in _RESERVED_NAMES:
        normalized = "_" + normalized
    return normalized


def _confined(root: Path, raw: object, field: str) -> Path:
    value = _nonempty_string(raw, field)
    lexical = value.replace("\\", "/")
    components = lexical.split("/")
    if (
        any(component == ".." for component in components)
        or lexical.startswith("/")
        or re.match(r"^[A-Za-z]:", lexical)
        or value.startswith("\\")
    ):
        raise WorkspaceError(f"invalid {field}")
    candidate = Path(*[component for component in components if component not in {"", "."}])
    try:
        resolved = (root / candidate).resolve(strict=False)
        resolved.relative_to(root)
    except (OSError, ValueError):
        raise WorkspaceError(f"invalid {field}") from None
    return resolved


@dataclass(frozen=True)
class Workspace:
    root: Path
    display_name: str
    export_name: str
    email: str | None
    phone_pattern: str | None
    profile_dir: Path
    applications_dir: Path
    styles_dir: Path
    outputs_dir: Path

    @classmethod
    def load(cls, root: Path) -> "Workspace":
        try:
            root = Path(root).resolve(strict=True)
            if not root.is_dir():
                raise WorkspaceError("workspace root is not a directory")
            config_path = (root / "cvtool.toml").resolve(strict=True)
            config_path.relative_to(root)
            with config_path.open("rb") as source:
                config = tomllib.load(source)
        except WorkspaceError:
            raise
        except (OSError, ValueError, tomllib.TOMLDecodeError):
            raise WorkspaceError("invalid workspace configuration") from None
        if not isinstance(config, dict):
            raise WorkspaceError("invalid workspace configuration")
        profile = config.get("profile")
        paths = config.get("paths")
        ats = config.get("ats", {})
        if not isinstance(profile, dict) or not isinstance(paths, dict):
            raise WorkspaceError("invalid workspace configuration")
        if not isinstance(ats, dict):
            raise WorkspaceError("invalid workspace configuration")
        display_name = _nonempty_string(profile.get("display_name"), "display_name")
        export_value = profile.get("export_name")
        if export_value is None:
            export_source = profile["display_name"]
        else:
            if not isinstance(export_value, str) or not export_value.strip():
                raise WorkspaceError("invalid export_name")
            export_source = export_value
        export_name = _safe_export_name(export_source)
        email_value = profile.get("email")
        email = None if email_value is None else _nonempty_string(email_value, "email")
        phone_value = ats.get("phone_pattern")
        phone_pattern = None if phone_value is None else _nonempty_string(phone_value, "phone_pattern")
        if phone_pattern is not None:
            try:
                re.compile(phone_pattern)
            except (re.error, OverflowError, RecursionError):
                raise WorkspaceError("invalid phone_pattern") from None
        return cls(
            root=root,
            display_name=display_name,
            export_name=export_name,
            email=email,
            phone_pattern=phone_pattern,
            profile_dir=_confined(root, paths.get("profile"), "profile path"),
            applications_dir=_confined(root, paths.get("applications"), "applications path"),
            styles_dir=_confined(root, paths.get("styles"), "styles path"),
            outputs_dir=_confined(root, paths.get("outputs"), "outputs path"),
        )
