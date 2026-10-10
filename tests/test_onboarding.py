"""Deterministic routing classifier: setup / interview / capture / repair / application."""
from pathlib import Path

from cv_toolkit.onboarding import WorkspaceState, classify
from cv_toolkit.bootstrap import init_workspace


def _write_dir(tree: dict, base: Path) -> None:
    for rel, raw in tree.items():
        path = base / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(raw, (dict, list)):
            import json
            path.write_text(json.dumps(raw), encoding="utf-8")
        else:
            path.write_text(raw, encoding="utf-8")


# A real, non-synthetic candidate with a matching source registry and projection.
REAL_EVIDENCE = {
    "schema_version": "1",
    "candidate_id": "candidate.ana",
    "items": [
        {
            "id": "item.exp",
            "kind": "experience",
            "claims": [
                {
                    "id": "claim.backend",
                    "text": "Built a service.",
                    "status": "confirmed",
                    "publication": "allowed",
                    "sources": ["source.owner"],
                }
            ],
        }
    ],
}
REAL_REGISTRY = [
    {"source_id": "source.owner", "kind": "owner_supplied", "fingerprint": "v1"}
]
REAL_PROJECTION = {
    "schema_version": 1,
    "id": "projection.general",
    "label": "Ana",
    "sections": [
        {
            "id": "section.s",
            "label": "Experience",
            "item_ids": ["item.exp"],
            "claim_ids": ["claim.backend"],
        }
    ],
}


def test_not_a_workspace_routes_to_setup(tmp_path):
    state = classify(tmp_path / "missing")
    assert state.state == "unconfigured"
    assert state.load_skill == ""
    assert "cv init" in state.action


def test_empty_default_candidate_routes_to_interview_import(tmp_path):
    ws = init_workspace(tmp_path / "ws", name="Candidate")
    state = classify(ws)
    assert state.state == "missing_candidate"
    assert state.load_skill == "experience-capture"
    # Both interview and documented import are supported; only material gaps prompt questions.
    assert "experienced" not in state.action  # sanity
    assert "INTERVIEW" in state.action or "interview" in state.action.lower()
    assert 'IMPORT' in state.action
    assert 'material questions' in state.action


def test_synthetic_example_never_routes_to_ready(tmp_path):
    ws = init_workspace(tmp_path / "ws", name="Demo", example="developer")
    for rel in ("profile/projection.json",):
        _write_dir({rel: REAL_PROJECTION}, ws)
    state = classify(ws)
    assert state.state == "synthetic"
    assert state.load_skill == "experience-capture"
    assert "not a real candidate" in state.action


def test_real_candidate_without_projection_routes_to_capture(tmp_path):
    ws = init_workspace(tmp_path / "ws", name="Ana")
    _write_dir(
        {"profile/evidence.json": REAL_EVIDENCE, "profile/registry.json": REAL_REGISTRY},
        ws,
    )
    state = classify(ws)
    assert state.state == "partial_evidence"
    assert state.load_skill == "experience-capture"
    assert "projection" in state.action.lower()


def test_dangling_registry_routes_to_repair_not_ready(tmp_path):
    ws = init_workspace(tmp_path / "ws", name="Ana")
    _write_dir(
        {
            "profile/evidence.json": REAL_EVIDENCE,
            # Registry present but does not cover source.owner -> broken join.
            "profile/registry.json": [
                {"source_id": "source.other", "kind": "owner_supplied", "fingerprint": "v1"}
            ],
        },
        ws,
    )
    state = classify(ws)
    assert state.state == "malformed"
    assert state.load_skill == ""
    assert "registry" in state.action.lower()


def test_missing_registry_with_evidence_routes_to_repair(tmp_path):
    ws = init_workspace(tmp_path / "ws", name="Ana")
    _write_dir({"profile/evidence.json": REAL_EVIDENCE}, ws)
    state = classify(ws)
    assert state.state == "malformed"
    assert "registry" in state.action.lower()


def test_broken_evidence_json_routes_to_repair(tmp_path):
    ws = init_workspace(tmp_path / "ws", name="Ana")
    _write_dir({"profile/evidence.json": "{not valid json"}, ws)
    state = classify(ws)
    assert state.state == "malformed"


def test_broken_projection_routes_to_repair(tmp_path):
    ws = init_workspace(tmp_path / "ws", name="Ana")
    _write_dir(
        {
            "profile/evidence.json": REAL_EVIDENCE,
            "profile/registry.json": REAL_REGISTRY,
            "profile/projection.json": {"id": 12},
        },
        ws,
    )
    state = classify(ws)
    assert state.state == "malformed"
    assert "projection" in state.action.lower()


def test_ready_routes_to_application_workflow(tmp_path):
    ws = init_workspace(tmp_path / "ws", name="Ana")
    _write_dir(
        {
            "profile/evidence.json": REAL_EVIDENCE,
            "profile/registry.json": REAL_REGISTRY,
            "profile/projection.json": REAL_PROJECTION,
        },
        ws,
    )
    state = classify(ws)
    assert state.state == "ready"
    assert state.load_skill == "application-materials"
    assert "application-materials" in state.action


def test_as_context_is_bounded_and_never_leaks_candidate_text(tmp_path):
    ws = init_workspace(tmp_path / "ws", name="Ana")
    _write_dir(
        {
            "profile/evidence.json": REAL_EVIDENCE,
            "profile/registry.json": REAL_REGISTRY,
            "profile/projection.json": REAL_PROJECTION,
        },
        ws,
    )
    context = classify(ws).as_context()
    assert isinstance(context, dict) and "context" in context
    assert "Built a service." not in context["context"]  # private prose not exposed
    assert "Ana" not in context["context"]


# --- Regression: canonical validation, never a superficial shape check. ---


def test_invalid_claim_status_routes_to_repair_not_ready(tmp_path):
    # Claim status outside the canonical enum must never yield "ready".
    ws = init_workspace(tmp_path / "ws", name="Ana")
    evidence = dict(REAL_EVIDENCE)
    evidence["items"] = [
        {
            "id": "item.exp",
            "kind": "experience",
            "claims": [
                {
                    "id": "claim.backend",
                    "text": "Built a service.",
                    "status": "not-a-real-status",
                    "publication": "allowed",
                    "sources": ["source.owner"],
                }
            ],
        }
    ]
    _write_dir(
        {
            "profile/evidence.json": evidence,
            "profile/registry.json": REAL_REGISTRY,
            "profile/projection.json": REAL_PROJECTION,
        },
        ws,
    )
    state = classify(ws)
    assert state.state == "malformed"
    assert state.load_skill == ""
    assert state.state != "ready"


def test_invalid_item_kind_routes_to_repair_not_ready(tmp_path):
    ws = init_workspace(tmp_path / "ws", name="Ana")
    evidence = {
        "schema_version": "1",
        "candidate_id": "candidate.ana",
        "items": [
            {
                "id": "item.x",
                "kind": "not-a-kind",
                "claims": [
                    {
                        "id": "claim.c",
                        "text": "Work.",
                        "status": "confirmed",
                        "publication": "allowed",
                        "sources": ["source.owner"],
                    }
                ],
            }
        ],
    }
    _write_dir(
        {
            "profile/evidence.json": evidence,
            "profile/registry.json": REAL_REGISTRY,
        },
        ws,
    )
    state = classify(ws)
    assert state.state == "malformed"
    assert state.state != "ready"


def test_projection_wrong_schema_routes_to_repair(tmp_path):
    # Old, wrong schema: sections lack item_ids/claim_ids. Must not route ready.
    ws = init_workspace(tmp_path / "ws", name="Ana")
    projection = {
        "schema_version": 1,
        "id": "projection.general",
        "label": "Ana",
        "sections": [{"id": "section.s", "label": "Experience"}],
    }
    _write_dir(
        {
            "profile/evidence.json": REAL_EVIDENCE,
            "profile/registry.json": REAL_REGISTRY,
            "profile/projection.json": projection,
        },
        ws,
    )
    state = classify(ws)
    assert state.state == "malformed"
    assert "projection" in state.action.lower()


def test_projection_unpublishable_reference_routes_to_repair(tmp_path):
    # Claim referenced by the projection is superseded -> not publishable.
    ws = init_workspace(tmp_path / "ws", name="Ana")
    evidence = {
        "schema_version": "1",
        "candidate_id": "candidate.ana",
        "items": [
            {
                "id": "item.exp",
                "kind": "experience",
                "claims": [
                    {
                        "id": "claim.old",
                        "text": "Superseded work.",
                        "status": "superseded",
                        "publication": "allowed",
                        "sources": ["source.owner"],
                    }
                ],
            }
        ],
    }
    projection = {
        "schema_version": 1,
        "id": "projection.general",
        "label": "Ana",
        "sections": [
            {
                "id": "section.s",
                "label": "Experience",
                "item_ids": ["item.exp"],
                "claim_ids": ["claim.old"],
            }
        ],
    }
    _write_dir(
        {
            "profile/evidence.json": evidence,
            "profile/registry.json": REAL_REGISTRY,
            "profile/projection.json": projection,
        },
        ws,
    )
    state = classify(ws)
    assert state.state == "malformed"
    assert state.state != "ready"


def test_unsafe_profile_path_routes_to_repair_never_escapes(tmp_path):
    # A profile path that would escape the workspace must be rejected.
    ws = init_workspace(tmp_path / "ws", name="Ana")
    escaped = tmp_path / "escaped"
    (ws / "cvtool.toml").write_text(
        "[profile]\ndisplay_name = \"Ana\"\n\n"
        "[paths]\nprofile = \"../escaped\"\n"
        "applications = \"applications\"\nstyles = \"styles\"\noutputs = \"outputs\"\n",
        encoding="utf-8",
    )
    # Evidence exists at the *escaped* location, so a naive classifier would
    # find claims there; the confined workspace load must reject it instead.
    _write_dir(
        {"evidence.json": REAL_EVIDENCE, "registry.json": REAL_REGISTRY}, escaped
    )
    state = classify(ws)
    assert state.state == "malformed"
    assert not (escaped / "projection.json").exists()


def test_synthetic_registry_kind_routes_to_synthetic(tmp_path):
    # A registry declaring the packaged synthetic_fixture kind is synthetic
    # even if the candidate id is in the ordinary namespace.
    ws = init_workspace(tmp_path / "ws", name="Ana")
    evidence = dict(REAL_EVIDENCE)
    evidence["candidate_id"] = "candidate.ana"
    registry = [
        {"source_id": "source.owner", "kind": "synthetic_fixture", "fingerprint": "synthetic-example-v1"}
    ]
    _write_dir(
        {
            "profile/evidence.json": evidence,
            "profile/registry.json": registry,
            "profile/projection.json": REAL_PROJECTION,
        },
        ws,
    )
    state = classify(ws)
    assert state.state == "synthetic"
    assert state.load_skill == "experience-capture"