# tests/test_evidence.py
import json
from copy import deepcopy
from pathlib import Path

import pytest

from cv_toolkit.evidence import EvidenceError, build_source_registry, claim_index, load_evidence, publishable_claims


def record(*claims, kind="experience"):
    return {
        "schema_version": "1",
        "candidate_id": "candidate.synthetic",
        "items": [{"id": "item.one", "kind": kind, "claims": list(claims)}],
    }


def claim(claim_id="claim.one", status="confirmed", publication="allowed", text="Built tests."):
    return {
        "id": claim_id,
        "text": text,
        "status": status,
        "publication": publication,
        "sources": ["source.synthetic.1"],
    }


def write_json(tmp_path: Path, value: object) -> Path:
    path = tmp_path / "evidence.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


REGISTRY = {"source.synthetic.1": {
    "source_id": "source.synthetic.1", "kind": "synthetic", "fingerprint": "declared-v1"
}}


def test_valid_mixed_record_indexes_and_filters_without_mutation(tmp_path):
    value = record(
        claim(),
        claim("claim.uncertain", "uncertain"),
        claim("claim.restricted", "confirmed", "restricted"),
        claim("claim.old", "superseded"),
        kind="language",
    )
    path = write_json(tmp_path, value)
    loaded = load_evidence(path, REGISTRY)
    assert set(claim_index(loaded, REGISTRY)) == {"claim.one", "claim.uncertain", "claim.restricted", "claim.old"}
    assert set(publishable_claims(loaded, REGISTRY)) == {"claim.one"}
    assert loaded == value


def test_language_proficiency_is_item_level_when_supplied(tmp_path):
    value = record(claim(text="Conversational French."), kind="language")
    value["items"][0]["attributes"] = {"proficiency": "conversational"}
    loaded = load_evidence(write_json(tmp_path, value), REGISTRY)
    assert loaded["items"][0]["attributes"] == {"proficiency": "conversational"}


def test_preferences_do_not_require_engineering_fields(tmp_path):
    value = record(claim(text="Prefers field work."), kind="preference")
    assert load_evidence(write_json(tmp_path, value), REGISTRY)["items"][0]["kind"] == "preference"


def test_duplicate_json_keys_fail_closed(tmp_path):
    path = tmp_path / "duplicate.json"
    path.write_text('{"schema_version":"1","schema_version":"1","candidate_id":"x.y","items":[]}', encoding="utf-8")
    with pytest.raises(EvidenceError, match="duplicate JSON key"):
        load_evidence(path, REGISTRY)


@pytest.mark.parametrize("bad", [
    {"schema_version": "2", "candidate_id": "x.y", "items": []},
    {"schema_version": "1", "candidate_id": "X", "items": []},
    {"schema_version": "1", "candidate_id": "x.y", "items": []},
])
def test_bad_top_level_is_rejected(tmp_path, bad):
    with pytest.raises(EvidenceError):
        load_evidence(write_json(tmp_path, bad), REGISTRY)


def test_duplicate_item_and_claim_ids_fail(tmp_path):
    value = record(claim(), claim("claim.one"))
    with pytest.raises(EvidenceError, match="duplicate claim id"):
        load_evidence(write_json(tmp_path, value), REGISTRY)
    value = {
        "schema_version": "1", "candidate_id": "x.y", "items": [
            {"id": "same.id", "kind": "skill", "claims": [claim("claim.a")]},
            {"id": "same.id", "kind": "skill", "claims": [claim("claim.b")]},
        ],
    }
    with pytest.raises(EvidenceError, match="duplicate item id"):
        load_evidence(write_json(tmp_path, value), REGISTRY)


@pytest.mark.parametrize("field,value,error", [
    ("sources", [], "invalid claim sources"),
    ("sources", [""], "invalid claim sources"),
    ("status", "unknown", "unsupported claim status"),
    ("publication", "confidential", "unsupported publication value"),
    ("text", "", "invalid claim text"),
])
def test_claim_validation_is_closed(tmp_path, field, value, error):
    item_claim = claim()
    item_claim[field] = value
    with pytest.raises(EvidenceError, match=error):
        load_evidence(write_json(tmp_path, record(item_claim)), REGISTRY)


def test_all_preservation_statuses_are_retained_but_not_published(tmp_path):
    value = record(
        claim("claim.a", "approximate"),
        claim("claim.b", "uncertain"),
        claim("claim.c", "source_only"),
        claim("claim.d", "superseded"),
        claim("claim.e", "confirmed", "excluded"),
    )
    loaded = load_evidence(write_json(tmp_path, value), REGISTRY)
    assert len(loaded["items"][0]["claims"]) == 5
    assert set(publishable_claims(loaded, REGISTRY)) == {"claim.a"}


def test_claim_limitations_are_retained_through_selection(tmp_path):
    item_claim = claim()
    item_claim["limitations"] = ["no measured cycle-time result"]
    value = record(item_claim)
    loaded = load_evidence(write_json(tmp_path, value), REGISTRY)
    assert claim_index(loaded, REGISTRY)["claim.one"]["limitations"] == ["no measured cycle-time result"]
    assert publishable_claims(loaded, REGISTRY)["claim.one"]["limitations"] == ["no measured cycle-time result"]


def test_malformed_claim_limitations_are_rejected(tmp_path):
    item_claim = claim()
    item_claim["limitations"] = [None]
    with pytest.raises(EvidenceError, match="invalid claim limitations"):
        load_evidence(write_json(tmp_path, record(item_claim)), REGISTRY)


@pytest.mark.parametrize("field,value", [
    ("status", []), ("status", {}), ("status", None), ("status", 1), ("status", True),
    ("publication", []), ("publication", {}), ("publication", None), ("publication", 1), ("publication", True),
])
def test_malformed_enum_types_are_sanitized(tmp_path, field, value):
    item_claim = claim()
    item_claim[field] = value
    with pytest.raises(EvidenceError, match="unsupported"):
        load_evidence(write_json(tmp_path, record(item_claim)), REGISTRY)


@pytest.mark.parametrize("bad_kind", [[], {}, None, 1, True])
def test_item_kind_wrong_types_fail_through_load_and_index(tmp_path, bad_kind):
    value = record(claim())
    value["items"][0]["kind"] = bad_kind
    with pytest.raises(EvidenceError, match="unsupported item kind"):
        load_evidence(write_json(tmp_path, value), REGISTRY)
    with pytest.raises(EvidenceError, match="unsupported item kind"):
        claim_index(value, REGISTRY)


@pytest.mark.parametrize("field,value", [
    ("status", []), ("status", {}), ("status", None), ("status", 1), ("status", True),
    ("publication", []), ("publication", {}), ("publication", None), ("publication", 1), ("publication", True),
])
def test_enum_wrong_types_fail_through_load_and_index(tmp_path, field, value):
    item_claim = claim()
    item_claim[field] = value
    record_value = record(item_claim)
    with pytest.raises(EvidenceError, match="unsupported"):
        load_evidence(write_json(tmp_path, record_value), REGISTRY)
    with pytest.raises(EvidenceError, match="unsupported"):
        claim_index(record_value, REGISTRY)


def test_dangling_and_duplicate_registry_sources_fail_before_selection(tmp_path):
    value = record(claim())
    value["items"][0]["claims"][0]["sources"] = ["source.missing"]
    with pytest.raises(EvidenceError, match="dangling claim source"):
        load_evidence(write_json(tmp_path, value), REGISTRY)
    with pytest.raises(EvidenceError, match="duplicate source id"):
        build_source_registry([REGISTRY["source.synthetic.1"], REGISTRY["source.synthetic.1"]])
    with pytest.raises(EvidenceError, match="conflicting source id"):
        build_source_registry([
            REGISTRY["source.synthetic.1"],
            {"source_id": "source.synthetic.1", "kind": "other", "fingerprint": "declared-v2"},
        ])
    with pytest.raises(EvidenceError, match="source registry key mismatch"):
        load_evidence(write_json(tmp_path, record(claim())), {"source.other": REGISTRY["source.synthetic.1"]})


def test_optional_ownership_and_maturity_are_not_required(tmp_path):
    item_claim = claim()
    item_claim["ownership"] = "team"
    item_claim["maturity"] = "prototype"
    loaded = load_evidence(write_json(tmp_path, record(item_claim, kind="project")), REGISTRY)
    assert loaded["items"][0]["claims"][0]["maturity"] == "prototype"


def test_unknown_fields_and_dangling_record_input_fail(tmp_path):
    value = record(claim())
    value["extra"] = True
    with pytest.raises(EvidenceError, match="invalid record fields"):
        load_evidence(write_json(tmp_path, value), REGISTRY)
    with pytest.raises(EvidenceError, match="invalid record"):
        claim_index({"schema_version": "1"}, REGISTRY)


@pytest.mark.parametrize("status", ["confirmed", "approximate", "uncertain", "source_only", "superseded"])
@pytest.mark.parametrize("publication", ["allowed", "restricted", "excluded"])
def test_every_storage_and_publication_combination(tmp_path, status, publication):
    value = record(claim(status=status, publication=publication))
    path = write_json(tmp_path, value)
    before = path.read_bytes()
    loaded = load_evidence(path, REGISTRY)
    snapshot = deepcopy(loaded)
    selected = publishable_claims(loaded, REGISTRY)
    expected = {"claim.one"} if status in {"confirmed", "approximate"} and publication == "allowed" else set()
    assert set(selected) == expected
    assert loaded == snapshot == value
    assert path.read_bytes() == before


@pytest.mark.parametrize("kind", ["experience", "project", "education", "training", "award", "skill", "language", "preference", "identity"])
def test_all_kinds_preserve_supplied_fields_without_inventing_optional_data(tmp_path, kind):
    value = record(claim(text="Zoë 李 supplied this fact."), kind=kind)
    value["items"][0]["label"] = "Synthetic evidence"
    value["items"][0]["attributes"] = {"owner_supplied": "  exact value  "}
    assert load_evidence(write_json(tmp_path, value), REGISTRY) == value


@pytest.mark.parametrize("bad", [None, True, 1, "not-a-record", [], {}])
def test_bad_registry_records_have_sanitized_errors(bad):
    with pytest.raises(EvidenceError, match="invalid source registry record fields"):
        build_source_registry([bad])


@pytest.mark.parametrize("bad", [None, 1, True])
def test_noniterable_registry_input_has_sanitized_error(bad):
    with pytest.raises(EvidenceError, match="invalid source registry"):
        build_source_registry(bad)


def test_registry_generator_is_copied_without_reading_declared_fingerprint(tmp_path):
    source = dict(REGISTRY["source.synthetic.1"], fingerprint=str(tmp_path / "never-read-secret"))
    registry = build_source_registry(entry for entry in [source])
    assert registry == {source["source_id"]: source}
    source["fingerprint"] = "changed"
    assert registry["source.synthetic.1"]["fingerprint"] != "changed"
    assert load_evidence(write_json(tmp_path, record(claim())), registry) == record(claim())


@pytest.mark.parametrize("api", [claim_index, publishable_claims])
def test_selection_validates_unpublishable_claims_too(api):
    bad = claim("claim.restricted", status="superseded", publication="restricted")
    bad["sources"] = ["source.missing"]
    value = record(claim(), bad)
    snapshot = deepcopy(value)
    with pytest.raises(EvidenceError, match="dangling claim source"):
        api(value, REGISTRY)
    assert value == snapshot


def test_duplicate_claim_id_across_items_is_rejected(tmp_path):
    value = record(claim())
    value["items"].append({"id": "item.two", "kind": "award", "claims": [claim()]})
    with pytest.raises(EvidenceError, match="duplicate claim id"):
        load_evidence(write_json(tmp_path, value), REGISTRY)


@pytest.mark.parametrize("bad", [[], {}, None, True, 1, "", "  "])
def test_language_proficiency_must_be_a_supplied_nonempty_string(tmp_path, bad):
    value = record(claim(), kind="language")
    value["items"][0]["attributes"] = {"proficiency": bad}
    with pytest.raises(EvidenceError, match="invalid language proficiency"):
        load_evidence(write_json(tmp_path, value), REGISTRY)


@pytest.mark.parametrize("bad", [[], {}, None, True, 1, "", [""], [1]])
def test_limitations_are_nonempty_strings_owned_by_claim(tmp_path, bad):
    item_claim = claim()
    item_claim["limitations"] = bad
    with pytest.raises(EvidenceError, match="invalid claim limitations"):
        load_evidence(write_json(tmp_path, record(item_claim)), REGISTRY)


@pytest.mark.parametrize("raw", ["{", "null", "[]", "[" * 1100 + "0" + "]" * 1100,
                               "9" * 5000, '{"private":NaN}', '{"private":Infinity}'])
def test_invalid_json_has_sanitized_error(tmp_path, raw):
    path = tmp_path / "private-evidence.json"
    path.write_text(raw, encoding="utf-8")
    with pytest.raises(EvidenceError) as error:
        load_evidence(path, REGISTRY)
    assert str(error.value) in {"invalid evidence JSON", "invalid record", "invalid record fields"}
    assert "private" not in str(error.value)


def test_duplicate_nested_json_keys_fail_before_selection(tmp_path):
    raw = json.dumps(record(claim())).replace('"status": "confirmed"',
                                              '"status": "confirmed", "status": "superseded"')
    path = tmp_path / "evidence.json"
    path.write_text(raw, encoding="utf-8")
    with pytest.raises(EvidenceError, match="duplicate JSON key"):
        load_evidence(path, REGISTRY)


@pytest.mark.parametrize("level", ["record", "item", "claim"])
def test_closed_object_fields_reject_each_missing_or_extra_field(tmp_path, level):
    value = record(claim())
    obj = {"record": value, "item": value["items"][0], "claim": value["items"][0]["claims"][0]}[level]
    for field in list(obj):
        changed = deepcopy(value)
        target = {"record": changed, "item": changed["items"][0], "claim": changed["items"][0]["claims"][0]}[level]
        del target[field]
        with pytest.raises(EvidenceError, match=f"invalid {level} fields"):
            load_evidence(write_json(tmp_path, changed), REGISTRY)
    obj["private-extra"] = "must not appear in errors"
    with pytest.raises(EvidenceError, match=f"invalid {level} fields"):
        load_evidence(write_json(tmp_path, value), REGISTRY)
