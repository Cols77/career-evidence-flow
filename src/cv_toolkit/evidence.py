"""Offline validation and selection of canonical, owner-supplied evidence.

Registry fingerprints are declarations, not proof of source-byte freshness.
This module reads only the explicit evidence file; it never follows sources.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
import json
from pathlib import Path
import re
from typing import Any


class EvidenceError(ValueError):
    """A deterministic validation failure containing rule names only."""


_ID = re.compile(r"[a-z0-9][a-z0-9._-]+")
_SOURCE_ID = re.compile(r"source\.[a-z0-9][a-z0-9._-]+")
_KINDS = {"experience", "project", "education", "training", "award",
          "skill", "language", "preference", "identity"}
_STATUSES = {"confirmed", "approximate", "uncertain", "source_only", "superseded"}
_PUBLICATION = {"allowed", "restricted", "excluded"}
_TOP_FIELDS = {"schema_version", "candidate_id", "items"}
_ITEM_FIELDS = {"id", "kind", "claims"}
_CLAIM_FIELDS = {"id", "text", "status", "publication", "sources"}
_SOURCE_FIELDS = {"source_id", "kind", "fingerprint"}


def _nonempty(value: Any, rule: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceError(f"invalid {rule}")


def _identifier(value: Any, rule: str, pattern: re.Pattern[str] = _ID) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise EvidenceError(f"invalid {rule}")
    return value


def build_source_registry(records: Iterable[Mapping[str, str]]) -> dict[str, dict[str, str]]:
    """Copy a bounded registry, rejecting duplicate and conflicting definitions."""
    try:
        entries = iter(records)
    except TypeError:
        raise EvidenceError("invalid source registry") from None
    registry: dict[str, dict[str, str]] = {}
    for record in entries:
        if not isinstance(record, Mapping) or set(record) != _SOURCE_FIELDS:
            raise EvidenceError("invalid source registry record fields")
        source_id = _identifier(record["source_id"], "source id", _SOURCE_ID)
        for field in ("kind", "fingerprint"):
            _nonempty(record[field], "source registry value")
        copied = dict(record)
        if source_id in registry:
            rule = "duplicate" if registry[source_id] == copied else "conflicting"
            raise EvidenceError(f"{rule} source id")
        registry[source_id] = copied
    return registry


def _require_source_registry(registry: Mapping[str, Mapping[str, str]]) -> dict[str, dict[str, str]]:
    if not isinstance(registry, Mapping):
        raise EvidenceError("invalid source registry")
    records = []
    for key, record in registry.items():
        if not isinstance(key, str) or not isinstance(record, Mapping):
            raise EvidenceError("invalid source registry")
        if record.get("source_id") != key:
            raise EvidenceError("source registry key mismatch")
        records.append(record)
    return build_source_registry(records)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceError("duplicate JSON key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise EvidenceError("invalid evidence JSON")


def _object(value: Any, rule: str, required: set[str], optional: set[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise EvidenceError(f"invalid {rule}")
    if not required <= value.keys() or value.keys() - required - optional:
        raise EvidenceError(f"invalid {rule} fields")
    return value


def _unique(value: str, seen: set[str], rule: str) -> None:
    if value in seen:
        raise EvidenceError(f"duplicate {rule}")
    seen.add(value)


def _enum(value: Any, allowed: set[str], rule: str) -> None:
    if not isinstance(value, str) or value not in allowed:
        raise EvidenceError(f"unsupported {rule}")


def _nonempty_list(value: Any, rule: str) -> list[Any]:
    if not isinstance(value, list) or not value:
        raise EvidenceError(f"invalid {rule}")
    return value


def _validate_record(record: Any, registry: Mapping[str, Mapping[str, str]]) -> dict[str, Any]:
    known_sources = _require_source_registry(registry)
    top = _object(record, "record", _TOP_FIELDS, set())
    if top["schema_version"] != "1":
        raise EvidenceError("unsupported schema_version")
    _identifier(top["candidate_id"], "candidate_id")
    item_ids: set[str] = set()
    claim_ids: set[str] = set()
    for item in _nonempty_list(top["items"], "items"):
        obj = _object(item, "item", _ITEM_FIELDS, {"label", "attributes"})
        _unique(_identifier(obj["id"], "item id"), item_ids, "item id")
        _enum(obj["kind"], _KINDS, "item kind")
        if "label" in obj:
            _nonempty(obj["label"], "item label")
        if "attributes" in obj:
            if not isinstance(obj["attributes"], dict):
                raise EvidenceError("invalid item attributes")
            if obj["kind"] == "language" and "proficiency" in obj["attributes"]:
                _nonempty(obj["attributes"]["proficiency"], "language proficiency")
        for claim in _nonempty_list(obj["claims"], "item claims"):
            c = _object(claim, "claim", _CLAIM_FIELDS, {"ownership", "maturity", "limitations"})
            _unique(_identifier(c["id"], "claim id"), claim_ids, "claim id")
            _nonempty(c["text"], "claim text")
            _enum(c["status"], _STATUSES, "claim status")
            _enum(c["publication"], _PUBLICATION, "publication value")
            for source in _nonempty_list(c["sources"], "claim sources"):
                _identifier(source, "claim sources", _SOURCE_ID)
                if source not in known_sources:
                    raise EvidenceError("dangling claim source")
            for optional in ("ownership", "maturity"):
                if optional in c:
                    _nonempty(c[optional], f"claim {optional}")
            if "limitations" in c:
                for limitation in _nonempty_list(c["limitations"], "claim limitations"):
                    _nonempty(limitation, "claim limitations")
    return top


def load_evidence(path: Path, registry: Mapping[str, Mapping[str, str]]) -> dict[str, Any]:
    """Read one UTF-8 JSON file and validate every claim against the registry."""
    try:
        with Path(path).open("r", encoding="utf-8", newline="") as source:
            record = json.load(source, object_pairs_hook=_reject_duplicate_keys,
                               parse_constant=_reject_constant)
    except EvidenceError:
        raise
    except (OSError, ValueError, RecursionError):
        raise EvidenceError("invalid evidence JSON") from None
    return _validate_record(record, registry)


def claim_index(record: dict[str, Any], registry: Mapping[str, Mapping[str, str]]) -> dict[str, dict[str, Any]]:
    """Index all claims, validating even excluded and superseded claims first."""
    validated = _validate_record(record, registry)
    return {claim["id"]: claim for item in validated["items"] for claim in item["claims"]}


def publishable_claims(record: dict[str, Any], registry: Mapping[str, Mapping[str, str]]) -> dict[str, dict[str, Any]]:
    """Select confirmed/approximate allowed claims without altering stored data."""
    return {key: claim for key, claim in claim_index(record, registry).items()
            if claim["status"] in {"confirmed", "approximate"} and claim["publication"] == "allowed"}
