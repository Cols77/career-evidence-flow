import copy
import json

import pytest

from cv_toolkit.evidence import build_source_registry
from cv_toolkit.projection import load_projection
from cv_toolkit.records import ToolkitError


def fixture_evidence():
    registry = build_source_registry([{'source_id': 'source.answer', 'kind': 'answer', 'fingerprint': 'synthetic'}])
    evidence = {'schema_version': '1', 'candidate_id': 'candidate.example', 'items': [
        {'id': 'item.project', 'kind': 'project', 'claims': [
            {'id': 'claim.project', 'text': 'Built tests', 'status': 'confirmed', 'publication': 'allowed', 'sources': ['source.answer']} ]},
        {'id': 'item.course', 'kind': 'training', 'claims': [
            {'id': 'claim.course', 'text': 'Completed course', 'status': 'approximate', 'publication': 'allowed', 'sources': ['source.answer']} ]},
    ]}
    return evidence, registry


def projection_record():
    return {'schema_version': 1, 'id': 'projection.base', 'label': 'Base', 'sections': [
        {'id': 'section.projects', 'label': 'Projects', 'item_ids': ['item.course', 'item.project'], 'claim_ids': ['claim.project', 'claim.course']}
    ], 'skills': [{'name': 'Testing', 'claim_ids': ['claim.project']}], 'summary_claim_ids': ['claim.project']}


def test_projection_preserves_order_and_evidence(tmp_path):
    evidence, registry = fixture_evidence()
    original = copy.deepcopy(evidence)
    record = projection_record()
    path = tmp_path / 'projection.json'
    path.write_text(json.dumps(record), encoding='utf-8')
    assert load_projection(path, evidence, registry) == record
    assert evidence == original


@pytest.mark.parametrize('status,publication', [('source_only', 'allowed'), ('superseded', 'allowed'), ('confirmed', 'restricted'), ('confirmed', 'excluded')])
def test_projection_never_promotes_unpublishable_claims(tmp_path, status, publication):
    evidence, registry = fixture_evidence()
    evidence['items'][0]['claims'][0].update(status=status, publication=publication)
    path = tmp_path / 'projection.json'
    path.write_text(json.dumps(projection_record()), encoding='utf-8')
    with pytest.raises(ToolkitError):
        load_projection(path, evidence, registry)


@pytest.mark.parametrize('mutation', ['wrong_owner', 'dangling', 'duplicate_section', 'duplicate_claim', 'unknown_field', 'boolean_schema'])
def test_projection_rejects_invalid_selection(tmp_path, mutation):
    evidence, registry = fixture_evidence()
    record = projection_record()
    section = record['sections'][0]
    if mutation == 'wrong_owner':
        section['item_ids'] = ['item.course']
    elif mutation == 'dangling':
        section['item_ids'].append('item.missing')
    elif mutation == 'duplicate_section':
        record['sections'].append(copy.deepcopy(section))
    elif mutation == 'duplicate_claim':
        section['claim_ids'].append('claim.project')
    elif mutation == 'unknown_field':
        record['secret'] = 'x'
    else:
        record['schema_version'] = True
    path = tmp_path / 'projection.json'
    path.write_text(json.dumps(record), encoding='utf-8')
    with pytest.raises(ToolkitError):
        load_projection(path, evidence, registry)
