"""Deterministic workspace-state classifier for the toolkit entry hook.

This module is the single authored source for routing a Hermes session that is
launched inside a private toolkit workspace. ``classify`` reads only structural
records (workspace config, evidence, registry, projection manifests) and never
the candidate's private prose. It returns bounded routing intent: which host
workflow to load and the concrete next action.

Readiness is decided by the canonical validators, never by a reimplemented
shape check: the source registry is normalized through
:func:`cv_toolkit.evidence.build_source_registry` / ``_require_source_registry``,
every claim is validated by :func:`cv_toolkit.evidence.load_evidence`, projection
references by :func:`cv_toolkit.projection.load_projection`, and the profile
path stays confined thanks to :meth:`cv_toolkit.workspace.Workspace.load`.

Dependency contract for the installed Hermes plugin: the plugin's
``onboarding.py`` is a verbatim copy of this module and imports the
``cv_toolkit`` package. The installer bundles the needed dependency modules
(``cv_toolkit/{__init__,records,evidence,projection,workspace}.py``) next to the
plugin, so the hook is self-contained; alternatively ``cv_toolkit`` may be
explicitly installed/on ``sys.path`` in the host environment. OR the package is
unavailable, the hook refuses to bless any workflow (never reports ``ready``).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

try:  # Use this package's validators, never an unrelated global installation.
    from importlib import import_module
    package = __package__ if __package__ == 'cv_toolkit' else __package__ + '.cv_toolkit'
    records = import_module(package + '.records')
    evidence_module = import_module(package + '.evidence')
    projection_module = import_module(package + '.projection')
    workspace_module = import_module(package + '.workspace')
    ToolkitError, load_json = records.ToolkitError, records.load_json
    EvidenceError = evidence_module.EvidenceError
    build_source_registry = evidence_module.build_source_registry
    canonical_load_evidence = evidence_module.load_evidence
    _require_source_registry = evidence_module._require_source_registry
    canonical_load_projection = projection_module.load_projection
    Workspace, WorkspaceError = workspace_module.Workspace, workspace_module.WorkspaceError
    _CANONICAL = True
except Exception:  # pragma: no cover - only in a bare, misconfigured plugin env
    _CANONICAL = False


@dataclass(frozen=True)
class WorkspaceState:
    """Bounded routing result. No candidate private content is included."""

    state: str
    load_skill: str  # name of the workflow skill the host should load
    action: str      # one-line guidance for the host agent
    detail: Optional[str] = None
    evidence_present: bool = False
    registry_valid: bool = False
    projection_present: bool = False
    candidate_id: Optional[str] = None
    reasons: tuple = field(default_factory=tuple)

    def as_context(self) -> Dict[str, str]:
        """Render the routing intent as pre_llm_call context for Hermes."""
        text = self.action
        if self.load_skill:
            text += f" Load the {self.load_skill!r} workflow."
        if self.detail:
            text += " " + self.detail
        return {"context": text}


# Fixed, non-negotiable routing table (see AGENTS.md / docs/agent-hosts.md).
STATE_TO_SKILL = {
    "unconfigured": "",             # nothing to load; setup first
    "missing_candidate": "experience-capture",
    "synthetic": "experience-capture",
    "partial_evidence": "experience-capture",
    "malformed": "",                # repair before any workflow
    "ready": "application-materials",
}

_SYNTHETIC_ID_RE = re.compile(r"^candidate\.synthetic")
_SYNTHETIC_KIND = "synthetic_fixture"  # packaged example source kind
_EMPTY_CANDIDATE = "candidate.new"


class _BrokenRecord(Exception):
    """Sentinel raised when a record file is invalid and must be repaired."""


def _read_any(path: Path) -> Any:
    """Parse one record file with the canonical strict JSON loader.

    Returns the parsed value, or ``None`` when the file is absent (a distinct,
    normal case handled by callers). Raises ``_BrokenRecord`` when the file is
    present but unreadable / not valid JSON / exceeds record limits.
    """
    if not path.is_file():
        return None
    try:
        return load_json(path)
    except ToolkitError:
        raise _BrokenRecord(
            f"{path.name} is present but unreadable or not valid JSON; "
            f"repair it before continuing. Do not guess the candidate's facts."
        ) from None


def _registry_kinds(registry: Any) -> list:
    """Collect declared source ``kind`` values from a list- or dict-shaped file."""
    if isinstance(registry, list):
        return [rec.get("kind") for rec in registry if isinstance(rec, dict)]
    if isinstance(registry, dict):
        return [rec.get("kind") for rec in registry.values() if isinstance(rec, dict)]
    return []


def _is_synthetic(evidence: Any, registry: Any) -> bool:
    """True only for packaged synthetic example profiles, never for unverified text.

    A profile is synthetic when its candidate id uses the reserved
    ``candidate.synthetic`` namespace or the registry declares a source with the
    packaged ``synthetic_fixture`` kind (see the bundled examples).
    """
    candidate_id = evidence.get("candidate_id") if isinstance(evidence, dict) else None
    id_hit = isinstance(candidate_id, str) and bool(_SYNTHETIC_ID_RE.match(candidate_id))
    return id_hit or _SYNTHETIC_KIND in _registry_kinds(registry)


def _normalize_registry(registry: Any) -> dict:
    """Return the canonical source registry dict, or raise ``_BrokenRecord``.

    Accepts the two persisted shapes (list of records, or dict keyed by
    source_id) and hands both to the canonical registry validators.
    """
    if registry is None:
        raise _BrokenRecord(
            "candidate evidence exists but the source registry is missing; "
            "repair the registry and evidence files before capturing new facts."
        )
    if not isinstance(registry, (list, dict)):
        raise _BrokenRecord(
            "the source registry is present but has an unsupported shape; "
            "repair it before capturing new facts."
        )
    try:
        if isinstance(registry, list):
            return build_source_registry(registry)
        return _require_source_registry(registry)
    except (EvidenceError, ToolkitError, TypeError, ValueError):
        raise _BrokenRecord(
            "candidate evidence exists but the source registry is invalid, "
            "unreadable, or does not cover the evidence's claims (dangling "
            "source join). Repair the registry and evidence files before "
            "capturing new facts."
        ) from None


def _has_claims(evidence: Any) -> bool:
    """Presence check only: any item carrying at least one claim. Not validation."""
    return (
        isinstance(evidence, dict)
        and isinstance(evidence.get("items"), list)
        and any(
            isinstance(item, dict)
            and isinstance(item.get("claims"), list)
            and item["claims"]
            for item in evidence["items"]
        )
    )


def classify(root: Path) -> WorkspaceState:
    """Return deterministic routing for the workspace rooted at ``root``.

    Order of checks matters and is intentional:
      1. not a toolkit workspace            -> unconfigured (setup first)
      2. config unreadable / malformed / unsafe path
                                             -> malformed (repair)
      3. synthetic example profile          -> synthetic (never "ready")
      4. no candidate / empty evidence      -> missing_candidate (interview/import)
      5. broken record files                -> malformed (repair)
      6. evidence not canonically valid / registry incomplete
                                             -> malformed (repair)
      7. valid evidence, no projection      -> partial_evidence (capture)
      8. evidence + canonically valid projection
                                             -> ready (application workflow)
    """
    root = Path(root).resolve()
    if not (root / "cvtool.toml").is_file():
        return WorkspaceState(
            state="unconfigured",
            load_skill=STATE_TO_SKILL["unconfigured"],
            action=(
                "This path is not a configured resume-toolkit workspace "
                "(no cvtool.toml). Do not invent a candidate. Guide the user to "
                "create a private workspace with the venv cv executable "
                "(`cv init <PRIVATE-WORKSPACE>`), then open that workspace in "
                "your host and reload the entry workflow."
            ),
        )

    if not _CANONICAL:
        return _malformed('Bundled validators are unavailable; reinstall the entry hook.')

    # Canonical workspace load confines the configured profile path.
    try:
        workspace = Workspace.load(root)
    except WorkspaceError:
        return _malformed(
            "workspace configuration (cvtool.toml) is unreadable, malformed, "
            "or points outside the workspace root; repair it before continuing. "
            "Do not guess the candidate's facts."
        )


    profile = workspace.profile_dir
    evidence_path = profile / "evidence.json"
    registry_path = profile / "registry.json"
    projection_path = profile / "projection.json"

    if any(not path.resolve().is_relative_to(root) for path in
           (evidence_path, registry_path, projection_path)):
        return _malformed('A profile record escapes the private workspace; repair its path.')

    try:
        evidence_raw = _read_any(evidence_path)
        registry_raw = _read_any(registry_path)
        projection_raw = _read_any(projection_path)
    except _BrokenRecord as exc:
        return _malformed(str(exc))

    candidate_id = evidence_raw.get("candidate_id") if isinstance(evidence_raw, dict) else None

    # 3. Synthetic example profiles are never a real candidate.
    if _is_synthetic(evidence_raw, registry_raw):
        return WorkspaceState(
            state="synthetic",
            load_skill=STATE_TO_SKILL["synthetic"],
            evidence_present=evidence_raw is not None,
            candidate_id=candidate_id if isinstance(candidate_id, str) else None,
            action=(
                "This workspace holds a synthetic example profile, not a real "
                "candidate. It is a fixture for exercising the toolkit and must "
                "never be treated as the user's actual experience. Use a real "
                "private workspace and capture the user's evidence there."
            ),
        )

    # 4. No candidate yet: empty evidence is a missing candidate, not "ready".
    if not _has_claims(evidence_raw):
        if evidence_path.exists() and evidence_raw != {
            'schema_version': '1', 'candidate_id': 'candidate.new', 'items': []
        }:
            return _malformed('The evidence record has no valid claims; repair its structure.')
        is_empty_default = isinstance(evidence_raw, dict) and evidence_raw.get(
            "candidate_id"
        ) == _EMPTY_CANDIDATE
        return WorkspaceState(
            state="missing_candidate",
            load_skill=STATE_TO_SKILL["missing_candidate"],
            evidence_present=evidence_raw is not None,
            candidate_id=candidate_id if isinstance(candidate_id, str) else None,
            action=(
                "No candidate evidence is recorded yet. Use the "
                "experience-capture workflow to INTERVIEW the user or IMPORT a "
                "source resume, then record real facts with sources and "
                "ownership. Use supplied resume facts with provenance; ask only "
                "material questions for gaps or uncertain claims. "
                "Do not build a projection or draft on empty evidence."
                + (
                    " It looks like the freshly created empty default profile "
                    "('candidate.new'); capture the real candidate now."
                    if is_empty_default
                    else ""
                )
            ),
        )

    # 5+6. Evidence exists: normalize the registry and validate every claim
    # against it with the canonical validators.
    try:
        registry = _normalize_registry(registry_raw)
        evidence = canonical_load_evidence(evidence_path, registry)
    except (EvidenceError, ToolkitError) as exc:
        return _malformed(
            "candidate evidence exists but is not canonically valid against "
            "the source registry "
            f"({exc}); repair the evidence and registry files before "
            "capturing new facts. Do not guess the candidate's facts."
        )
    except _BrokenRecord as exc:
        return _malformed(str(exc))

    # 7+8. Projection state, validated against the canonical evidence.
    if not projection_path.is_file():
        return WorkspaceState(
            state="partial_evidence",
            load_skill=STATE_TO_SKILL["partial_evidence"],
            evidence_present=True,
            registry_valid=True,
            projection_present=False,
            action=(
                "Candidate evidence is captured and the registry is valid, but "
                "no projection exists yet. Continue the experience-capture "
                "workflow to select ordered, publishable evidence into a "
                "projection (and run `cv validate-evidence` / "
                "`cv validate-projection`), then move to application materials."
            ),
        )

    if not (
        isinstance(projection_raw, dict)
        and isinstance(projection_raw.get("schema_version"), int)
    ):
        return _malformed(
            "a projection file exists but is invalid (unreadable or wrong "
            "shape). Repair the projection before drafting."
        )

    try:
        canonical_load_projection(projection_path, evidence, registry)
    except ToolkitError:
        return _malformed(
            "a projection file exists but is invalid: it fails canonical "
            "projection validation (wrong shape, duplicate selections, or "
            "references that are not published or not selected). Repair the "
            "projection before drafting."
        )

    return WorkspaceState(
        state="ready",
        load_skill=STATE_TO_SKILL["ready"],
        evidence_present=True,
        registry_valid=True,
        projection_present=True,
        candidate_id=candidate_id if isinstance(candidate_id, str) else None,
        action=(
            "The candidate workspace is ready for the application workflow. "
            "Load the application-materials workflow: obtain the complete job "
            "description, freeze it with `cv create-application`, map "
            "requirements to real evidence, ask only material unanswered "
            "questions, then draft and run independent reviews."
        ),
    )


def _malformed(detail: str) -> WorkspaceState:
    action = (
        "The workspace records are malformed and must be repaired before "
        "any workflow continues. Run the CLI validators explicitly and fix "
        "the stated files; do not rewrite candidate facts or guess missing "
        "evidence."
    )
    if detail:
        action += " " + detail
    return WorkspaceState(
        state="malformed",
        load_skill=STATE_TO_SKILL["malformed"],
        action=action,
        detail=detail,
    )