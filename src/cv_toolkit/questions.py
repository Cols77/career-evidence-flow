"""Durable actual answers and explicit evidence/gap dispositions.

Actual answers live here with their supplied provenance and correction history.
The application answers.json file is reserved and must remain empty.
"""
from copy import deepcopy
from datetime import datetime

from .projection import evidence_claims, selected_claims
from .records import ToolkitError, atomic_write_json, identifier, identifiers, load_json, nonempty, object_fields, schema

STATUSES = {'pending', 'answered', 'resolved', 'unknown', 'declined', 'not_needed'}
ACTIONS = {'update_evidence', 'retain_existing', 'omit_claim', 'record_gap'}


def _answer(answer):
    object_fields(answer, {'text', 'source_id', 'recorded_at'}, rule='answer')
    nonempty(answer['text'], 'answer text')
    identifier(answer['source_id'], 'answer source id', source=True)
    nonempty(answer['recorded_at'], 'answer timestamp')
    try:
        timestamp = datetime.fromisoformat(answer['recorded_at'].replace('Z', '+00:00'))
        if timestamp.tzinfo is None:
            raise ValueError
    except ValueError:
        raise ToolkitError('invalid answer timestamp') from None


def _resolution(resolution, claims=None):
    object_fields(resolution, {'action', 'claim_ids', 'rationale'}, rule='resolution')
    if not isinstance(resolution['action'], str) or resolution['action'] not in ACTIONS:
        raise ToolkitError('invalid resolution action')
    nonempty(resolution['rationale'], 'resolution rationale')
    positive = resolution['action'] in {'update_evidence', 'retain_existing'}
    identifiers(resolution['claim_ids'], 'resolution claim ids', nonempty_list=positive)
    if not positive and resolution['claim_ids']:
        raise ToolkitError('gap resolution cannot assert claims')
    if claims is not None:
        selected_claims(resolution['claim_ids'], claims, 'resolution claim ids', required=positive)


def _validate(record, claims=None):
    object_fields(record, {'schema_version', 'questions'}, rule='questions')
    schema(record['schema_version'])
    if not isinstance(record['questions'], list):
        raise ToolkitError('invalid questions list')
    seen = set()
    for question in record['questions']:
        object_fields(question, {'id', 'prompt', 'reason', 'unlocks', 'status', 'material'}, {'answer', 'resolution', 'history'}, rule='question')
        question_id = identifier(question['id'], 'question id')
        if question_id in seen:
            raise ToolkitError('duplicate question id')
        seen.add(question_id)
        nonempty(question['prompt'], 'question prompt')
        nonempty(question['reason'], 'question reason')
        identifiers(question['unlocks'], 'question unlocks')
        if not isinstance(question['status'], str) or question['status'] not in STATUSES or type(question['material']) is not bool:
            raise ToolkitError('invalid question status or materiality')
        if 'answer' in question:
            _answer(question['answer'])
        if question['status'] == 'answered' and 'answer' not in question:
            raise ToolkitError('answered question requires actual answer')
        if 'history' in question:
            if not isinstance(question['history'], list) or 'answer' not in question:
                raise ToolkitError('invalid answer history')
            for answer in question['history']:
                _answer(answer)
        if 'resolution' in question:
            if question['status'] in {'pending', 'answered'}:
                raise ToolkitError('unresolved question cannot carry a disposition')
            _resolution(question['resolution'], claims)
            if question['status'] in {'unknown', 'declined'} and question['resolution']['action'] not in {'omit_claim', 'record_gap'}:
                raise ToolkitError('unknown question requires gap disposition')
        if question['status'] in {'resolved', 'not_needed', 'unknown', 'declined'} and 'resolution' not in question:
            raise ToolkitError('terminal question requires disposition')
    return record


def load_questions(path, evidence, registry):
    record = _validate(load_json(path), evidence_claims(evidence, registry))
    for question in record['questions']:
        answers = question.get('history', []) + ([question['answer']] if 'answer' in question else [])
        if any(answer['source_id'] not in registry for answer in answers):
            raise ToolkitError('dangling answer source')
    return record


def pending_questions(record):
    _validate(record)
    return [question for question in record['questions'] if question['material'] and question['status'] in {'pending', 'answered'}]


def _find(record, question_id):
    identifier(question_id, 'question id')
    for question in record['questions']:
        if question['id'] == question_id:
            return question
    raise ToolkitError('unknown question id')


def record_answer(path, question_id, text, source_id, recorded_at, *, correction=False):
    answer = {'text': text, 'source_id': source_id, 'recorded_at': recorded_at}
    _answer(answer)
    record = _validate(load_json(path))
    question = _find(record, question_id)
    existing = question.get('answer')
    if existing == answer:
        return record
    if existing is not None:
        if correction is not True:
            raise ToolkitError('answer correction requires explicit authorization')
        if datetime.fromisoformat(recorded_at.replace('Z', '+00:00')) < datetime.fromisoformat(existing['recorded_at'].replace('Z', '+00:00')):
            raise ToolkitError('answer correction predates existing answer')
        question.setdefault('history', []).append(deepcopy(existing))
    question['answer'] = answer
    question['status'] = 'answered'
    question.pop('resolution', None)
    _validate(record)
    atomic_write_json(path, record)
    return record


def resolve_question(path, question_id, resolution, evidence, registry, status='resolved'):
    if not isinstance(status, str) or status not in {'resolved', 'unknown', 'declined', 'not_needed'}:
        raise ToolkitError('invalid resolved question status')
    claims = evidence_claims(evidence, registry)
    _resolution(resolution, claims)
    if status in {'unknown', 'declined'} and resolution['action'] not in {'omit_claim', 'record_gap'}:
        raise ToolkitError('unknown question requires gap disposition')
    record = load_questions(path, evidence, registry)
    question = _find(record, question_id)
    if question.get('resolution') == resolution and question['status'] == status:
        return record
    question['resolution'] = deepcopy(resolution)
    question['status'] = status
    _validate(record, claims)
    atomic_write_json(path, record)
    return record
