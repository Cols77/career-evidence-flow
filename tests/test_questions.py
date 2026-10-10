import json

import pytest

from cv_toolkit.questions import load_questions, pending_questions, record_answer, resolve_question
from cv_toolkit.records import ToolkitError, atomic_write_json
from test_projection import fixture_evidence


def question_record():
    return {'schema_version': 1, 'questions': [{'id': 'question.testing', 'prompt': 'What did you build?', 'reason': 'Ownership is missing', 'unlocks': ['requirement.testing'], 'status': 'pending', 'material': True}]}


def test_answers_are_actual_idempotent_and_corrections_explicit(tmp_path):
    path = tmp_path / 'questions.json'
    atomic_write_json(path, question_record())
    record_answer(path, 'question.testing', 'I observed testing.', 'source.answer', '2026-10-10T10:00:00Z')
    before = path.stat().st_mtime_ns
    original = path.read_bytes()
    record_answer(path, 'question.testing', 'I observed testing.', 'source.answer', '2026-10-10T10:00:00Z')
    assert path.stat().st_mtime_ns == before
    with pytest.raises(ToolkitError):
        record_answer(path, 'question.testing', 'I built testing.', 'source.answer', '2026-10-10T11:00:00Z')
    assert path.read_bytes() == original
    record_answer(path, 'question.testing', 'I built testing.', 'source.answer', '2026-10-10T11:00:00Z', correction=True)
    question = json.loads(path.read_text())['questions'][0]
    assert question['answer']['text'] == 'I built testing.'
    assert question['history'][0]['text'] == 'I observed testing.'
    assert question['status'] == 'answered'


@pytest.mark.parametrize('field,value', [('text', ''), ('source_id', ''), ('recorded_at', ''), ('recorded_at', 'yesterday')])
def test_invalid_answer_never_changes_file(tmp_path, field, value):
    path = tmp_path / 'questions.json'
    atomic_write_json(path, question_record())
    before = path.read_bytes()
    args = {'text': 'Actual answer', 'source_id': 'source.answer', 'recorded_at': '2026-10-10T10:00:00Z'}
    args[field] = value
    with pytest.raises(ToolkitError):
        record_answer(path, 'question.testing', **args)
    assert path.read_bytes() == before


@pytest.mark.parametrize('action,status', [('omit_claim', 'declined'), ('record_gap', 'unknown')])
def test_gap_dispositions_allow_narrow_truthful_drafts(tmp_path, action, status):
    evidence, registry = fixture_evidence()
    path = tmp_path / 'questions.json'
    atomic_write_json(path, question_record())
    resolve_question(path, 'question.testing', {'action': action, 'claim_ids': [], 'rationale': 'Do not claim ownership'}, evidence, registry, status=status)
    record = load_questions(path, evidence, registry)
    assert pending_questions(record) == []
    assert 'answer' not in record['questions'][0]


def test_resolution_rejects_unpublishable_claim_without_mutation(tmp_path):
    evidence, registry = fixture_evidence()
    evidence['items'][0]['claims'][0]['publication'] = 'restricted'
    path = tmp_path / 'questions.json'
    atomic_write_json(path, question_record())
    before = path.read_bytes()
    with pytest.raises(ToolkitError):
        resolve_question(path, 'question.testing', {'action': 'retain_existing', 'claim_ids': ['claim.project'], 'rationale': 'Use known evidence'}, evidence, registry)
    assert path.read_bytes() == before


def test_answer_provenance_must_join_registry(tmp_path):
    evidence, registry = fixture_evidence()
    path = tmp_path / 'questions.json'
    record = question_record()
    record['questions'][0].update(status='answered', answer={'text': 'Actual answer', 'source_id': 'source.missing', 'recorded_at': '2026-10-10T10:00:00Z'})
    atomic_write_json(path, record)
    with pytest.raises(ToolkitError):
        load_questions(path, evidence, registry)


def test_malformed_resolution_action_is_structured_and_preserves_file(tmp_path):
    evidence, registry = fixture_evidence()
    path = tmp_path / 'questions.json'
    atomic_write_json(path, question_record())
    before = path.read_bytes()
    with pytest.raises(ToolkitError):
        resolve_question(path, 'question.testing', {'action': [], 'claim_ids': [], 'rationale': 'Narrow wording'}, evidence, registry)
    assert path.read_bytes() == before


def test_loading_unknown_question_cannot_retain_positive_claims(tmp_path):
    evidence, registry = fixture_evidence()
    path = tmp_path / 'questions.json'
    record = question_record()
    record['questions'][0].update(status='unknown', resolution={'action': 'retain_existing', 'claim_ids': ['claim.project'], 'rationale': 'Still unknown'})
    atomic_write_json(path, record)
    with pytest.raises(ToolkitError):
        load_questions(path, evidence, registry)


@pytest.mark.parametrize('status', ['unknown', 'declined'])
def test_terminal_gap_status_requires_explicit_disposition(tmp_path, status):
    evidence, registry = fixture_evidence()
    path = tmp_path / 'questions.json'
    record = question_record()
    record['questions'][0]['status'] = status
    atomic_write_json(path, record)
    before = path.read_bytes()
    with pytest.raises(ToolkitError):
        load_questions(path, evidence, registry)
    with pytest.raises(ToolkitError):
        pending_questions(record)
    assert path.read_bytes() == before


@pytest.mark.parametrize('status', ['pending', 'answered'])
def test_unresolved_question_cannot_carry_a_disposition(tmp_path, status):
    evidence, registry = fixture_evidence()
    path = tmp_path / 'questions.json'
    record = question_record()
    question = record['questions'][0]
    question.update(status=status, resolution={'action': 'record_gap', 'claim_ids': [], 'rationale': 'Keep wording narrow'})
    if status == 'answered':
        question['answer'] = {'text': 'Actual answer', 'source_id': 'source.answer', 'recorded_at': '2026-10-10T10:00:00Z'}
    atomic_write_json(path, record)
    before = path.read_bytes()
    with pytest.raises(ToolkitError):
        load_questions(path, evidence, registry)
    with pytest.raises(ToolkitError):
        pending_questions(record)
    assert path.read_bytes() == before


def test_pending_questions_counts_actual_unresolved_material_questions():
    record = question_record()
    answered = dict(record['questions'][0], id='question.answered', status='answered', answer={'text': 'Actual answer', 'source_id': 'source.answer', 'recorded_at': '2026-10-10T10:00:00Z'})
    immaterial = dict(record['questions'][0], id='question.optional', material=False)
    unknown = dict(record['questions'][0], id='question.unknown', status='unknown', resolution={'action': 'record_gap', 'claim_ids': [], 'rationale': 'Keep wording narrow'})
    record['questions'].extend([answered, immaterial, unknown])
    assert [question['id'] for question in pending_questions(record)] == ['question.testing', 'question.answered']
