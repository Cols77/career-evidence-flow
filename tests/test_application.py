import copy
import hashlib
import json
from types import SimpleNamespace

import pytest

from cv_toolkit.application import create_application, load_application, validate_requirements
from cv_toolkit.records import ToolkitError, atomic_write_json
from test_projection import fixture_evidence, projection_record


def requirement_record():
    return {'schema_version': 1, 'requirements': [{'id': 'requirement.testing', 'text': 'Build tests', 'priority': 'required', 'status': 'confirmed', 'claim_ids': ['claim.project'], 'rationale': 'Direct project evidence', 'source_text': 'Build tests'}]}


def create(tmp_path):
    projection = tmp_path / 'profile' / 'base.json'
    projection.parent.mkdir()
    atomic_write_json(projection, projection_record())
    workspace = SimpleNamespace(root=tmp_path, applications_dir=tmp_path / 'applications')
    root = create_application(workspace, 'example-role', 'Build tests\r\nUse Python.', 'Example Company', 'Engineer', 'profile/base.json')
    return root


def test_application_freezes_bytes_and_cannot_overwrite(tmp_path):
    evidence, registry = fixture_evidence()
    root = create(tmp_path)
    manifest = load_application(root, evidence, registry)
    assert manifest['extraction_complete'] is False
    assert manifest['policy']['deliverables'] == ['resume', 'cover_letter']
    assert (root / manifest['job_source']).read_bytes() == b'Build tests\r\nUse Python.'
    before = (root / 'application.json').read_bytes()
    workspace = SimpleNamespace(root=tmp_path, applications_dir=tmp_path / 'applications')
    with pytest.raises(ToolkitError):
        create_application(workspace, 'example-role', 'Changed job', 'Example', 'Engineer', 'profile/base.json')
    assert (root / 'application.json').read_bytes() == before
    (root / manifest['job_source']).write_bytes(b'Changed job')
    with pytest.raises(ToolkitError):
        load_application(root, evidence, registry)


@pytest.mark.parametrize('mutation', ['positive_empty', 'unknown_claims', 'duplicate', 'source_only'])
def test_requirements_mapping_is_truthful(mutation):
    evidence, registry = fixture_evidence()
    record = requirement_record()
    requirement = record['requirements'][0]
    if mutation == 'positive_empty':
        requirement['claim_ids'] = []
    elif mutation == 'unknown_claims':
        requirement['status'] = 'unknown'
    elif mutation == 'duplicate':
        record['requirements'].append(copy.deepcopy(requirement))
    else:
        evidence['items'][0]['claims'][0]['status'] = 'source_only'
    with pytest.raises(ToolkitError):
        validate_requirements(record, evidence, registry)


def test_application_checks_jd_substrings_and_confined_paths(tmp_path):
    evidence, registry = fixture_evidence()
    root = create(tmp_path)
    requirements = requirement_record()
    requirements['requirements'][0]['source_text'] = 'Invented instruction'
    atomic_write_json(root / 'requirements.json', requirements)
    with pytest.raises(ToolkitError):
        load_application(root, evidence, registry)
    atomic_write_json(root / 'requirements.json', {'schema_version': 1, 'requirements': []})
    manifest = json.loads((root / 'application.json').read_text())
    manifest['projection'] = '../profile/base.json'
    atomic_write_json(root / 'application.json', manifest)
    with pytest.raises(ToolkitError):
        load_application(root, evidence, registry)


def test_invalid_creation_policy_performs_no_application_writes(tmp_path):
    projection = tmp_path / 'base.json'
    atomic_write_json(projection, projection_record())
    workspace = SimpleNamespace(root=tmp_path, applications_dir=tmp_path / 'applications')
    with pytest.raises(ToolkitError):
        create_application(workspace, 'example-role', 'JD', 'Example', 'Engineer', 'base.json', policy={'ai_use': 'invented'})
    assert not workspace.applications_dir.exists()


def test_malformed_deliverable_is_structured_and_performs_no_writes(tmp_path):
    projection = tmp_path / 'base.json'
    atomic_write_json(projection, projection_record())
    workspace = SimpleNamespace(root=tmp_path, applications_dir=tmp_path / 'applications')
    with pytest.raises(ToolkitError):
        create_application(workspace, 'example-role', 'JD', 'Example', 'Engineer', 'base.json', policy={'deliverables': [[]]})
    assert not workspace.applications_dir.exists()


def test_creation_rejects_malformed_projection_before_writes(tmp_path):
    projection = tmp_path / 'base.json'
    record = projection_record()
    record['sections'][0]['item_ids'].append('item.project')
    atomic_write_json(projection, record)
    workspace = SimpleNamespace(root=tmp_path, applications_dir=tmp_path / 'applications')
    with pytest.raises(ToolkitError):
        create_application(workspace, 'example-role', 'JD', 'Example', 'Engineer', 'base.json')
    assert not workspace.applications_dir.exists()


@pytest.mark.parametrize('answer', [{'text': 'Unvalidated supplied text', 'source_id': 'source.missing'}, 'arbitrary answer'])
def test_reserved_answers_placeholder_cannot_store_unvalidated_entries(tmp_path, answer):
    evidence, registry = fixture_evidence()
    root = create(tmp_path)
    path = root / 'answers.json'
    atomic_write_json(path, {'schema_version': 1, 'answers': [answer]})
    before = path.read_bytes()
    with pytest.raises(ToolkitError) as error:
        load_application(root, evidence, registry)
    assert 'Unvalidated supplied text' not in str(error.value)
    assert path.read_bytes() == before
