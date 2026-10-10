"""Frozen job descriptions and truthful application requirement mappings.

Actual answers are stored with questions. The manifest's answers.json reference
reserves a future answer store; its answers list must remain empty until that
store has a defined provenance schema and validation implementation.
"""
from copy import deepcopy
import hashlib
from pathlib import Path
import re
import shutil

from .projection import evidence_claims, load_projection, selected_claims, validate_projection_structure
from .questions import load_questions
from .records import MAX_RECORD_BYTES, ToolkitError, atomic_write_json, confined, identifier, load_json, nonempty, object_fields, schema

DEFAULT_POLICY = {'deliverables': ['resume', 'cover_letter'], 'ai_use': 'allowed', 'max_resume_pages': 2, 'max_letter_pages': 1, 'min_letter_words': 0, 'max_letter_words': 450}
POSITIVE_STATUSES = {'confirmed', 'transferable', 'project_or_course_only'}
_REQUIRED = {'schema_version', 'slug', 'company', 'title', 'job_source', 'job_sha256', 'extraction_complete', 'projection', 'requirements', 'questions', 'answers', 'resume_source', 'resume_claims', 'policy'}
_OPTIONAL = {'location', 'work_model', 'cover_letter_source', 'cover_letter_claims'}


def validate_policy(policy):
    object_fields(policy, DEFAULT_POLICY.keys(), rule='application policy')
    deliverables = policy['deliverables']
    if not isinstance(deliverables, list) or not deliverables or any(not isinstance(entry, str) or entry not in {'resume', 'cover_letter'} for entry in deliverables) or len(set(deliverables)) != len(deliverables):
        raise ToolkitError('invalid application deliverables')
    if not isinstance(policy['ai_use'], str) or policy['ai_use'] not in {'allowed', 'restricted', 'forbidden'}:
        raise ToolkitError('invalid AI use policy')
    for field in ('max_resume_pages', 'max_letter_pages', 'min_letter_words', 'max_letter_words'):
        if type(policy[field]) is not int or policy[field] < (0 if field == 'min_letter_words' else 1):
            raise ToolkitError('invalid application policy limit')
    if policy['min_letter_words'] > policy['max_letter_words']:
        raise ToolkitError('invalid letter word limits')
    return policy


def validate_requirements(record, evidence, registry):
    claims = evidence_claims(evidence, registry)
    object_fields(record, {'schema_version', 'requirements'}, rule='requirements')
    schema(record['schema_version'])
    if not isinstance(record['requirements'], list):
        raise ToolkitError('invalid requirements list')
    seen = set()
    for requirement in record['requirements']:
        object_fields(requirement, {'id', 'text', 'priority', 'status', 'claim_ids', 'rationale'}, {'source_text'}, rule='requirement')
        requirement_id = identifier(requirement['id'], 'requirement id')
        if requirement_id in seen:
            raise ToolkitError('duplicate requirement id')
        seen.add(requirement_id)
        for field in ('text', 'rationale'):
            nonempty(requirement[field], f'requirement {field}')
        if not isinstance(requirement['priority'], str) or requirement['priority'] not in {'required', 'preferred', 'instruction'}:
            raise ToolkitError('invalid requirement priority')
        status = requirement['status']
        if not isinstance(status, str) or status not in POSITIVE_STATUSES | {'unsupported', 'unknown'}:
            raise ToolkitError('invalid requirement status')
        selected_claims(requirement['claim_ids'], claims, 'requirement claim ids', required=status in POSITIVE_STATUSES)
        if status in {'unsupported', 'unknown'} and requirement['claim_ids']:
            raise ToolkitError('unsupported requirement cannot assert claims')
        if 'source_text' in requirement:
            nonempty(requirement['source_text'], 'requirement source text')
    return record


def load_application(root, evidence, registry):
    root = Path(root)
    record = load_json(confined(root, 'application.json'))
    object_fields(record, _REQUIRED, _OPTIONAL, rule='application')
    schema(record['schema_version'])
    _slug(record['slug'])
    for field in ('company', 'title', 'location', 'work_model'):
        if field in record:
            nonempty(record[field], f'application {field}')
    if type(record['extraction_complete']) is not bool:
        raise ToolkitError('invalid extraction completion')
    if not isinstance(record['job_sha256'], str) or not re.fullmatch(r'[a-f0-9]{64}', record['job_sha256']):
        raise ToolkitError('invalid frozen job fingerprint')
    validate_policy(record['policy'])
    required_paths = {'job_source', 'projection', 'requirements', 'questions', 'answers'}
    paths = {field: confined(root, record[field], required=field in required_paths) for field in required_paths | {'resume_source', 'resume_claims', 'cover_letter_source', 'cover_letter_claims'} if field in record}
    if len(set(paths.values())) != len(paths):
        raise ToolkitError('application paths must be distinct')
    if ('cover_letter_source' in record) != ('cover_letter_claims' in record) or ('cover_letter' in record['policy']['deliverables'] and 'cover_letter_source' not in record):
        raise ToolkitError('missing cover letter paths')
    try:
        with paths['job_source'].open('rb') as stream:
            raw = stream.read(MAX_RECORD_BYTES + 1)
        if len(raw) > MAX_RECORD_BYTES:
            raise ToolkitError('job description exceeds limit')
        job_text = raw.decode('utf-8')
    except (OSError, UnicodeError):
        raise ToolkitError('unreadable job description') from None
    if hashlib.sha256(raw).hexdigest() != record['job_sha256']:
        raise ToolkitError('frozen job description changed')
    load_projection(paths['projection'], evidence, registry)
    requirements = validate_requirements(load_json(paths['requirements']), evidence, registry)
    for requirement in requirements['requirements']:
        if 'source_text' in requirement and requirement['source_text'] not in job_text:
            raise ToolkitError('requirement source text absent from frozen job')
    questions = load_questions(paths['questions'], evidence, registry)
    known_requirements = {requirement['id'] for requirement in requirements['requirements']}
    if any(requirement_id not in known_requirements for question in questions['questions'] for requirement_id in question['unlocks']):
        raise ToolkitError('dangling question requirement')
    answers = load_json(paths['answers'])
    object_fields(answers, {'schema_version', 'answers'}, rule='answers')
    schema(answers['schema_version'])
    if not isinstance(answers['answers'], list) or answers['answers']:
        raise ToolkitError('reserved answers store must be empty')
    return record


def _slug(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', value):
        raise ToolkitError('invalid application slug')
    return value


def create_application(workspace, slug, job_text, company, title, projection_path, policy=None):
    _slug(slug)
    nonempty(job_text, 'job description')
    nonempty(company, 'application company')
    nonempty(title, 'application title')
    raw = job_text.encode('utf-8')
    if len(raw) > MAX_RECORD_BYTES:
        raise ToolkitError('job description exceeds limit')
    merged_policy = deepcopy(DEFAULT_POLICY)
    if policy is not None:
        if not isinstance(policy, dict) or policy.keys() - DEFAULT_POLICY.keys():
            raise ToolkitError('invalid application policy fields')
        merged_policy.update(deepcopy(policy))
    validate_policy(merged_policy)
    projection = load_json(confined(workspace.root, projection_path))
    validate_projection_structure(projection)
    try:
        root = Path(workspace.root).resolve(strict=True)
        application_parent = Path(workspace.applications_dir).resolve(strict=False)
        relative_parent = application_parent.relative_to(root).as_posix()
        destination = confined(root, relative_parent + '/' + slug, required=False)
    except (OSError, ValueError):
        raise ToolkitError('invalid applications directory') from None
    if destination.exists():
        raise ToolkitError('application already exists')
    record = {'schema_version': 1, 'slug': slug, 'company': company, 'title': title, 'job_source': 'job.txt', 'job_sha256': hashlib.sha256(raw).hexdigest(), 'extraction_complete': False, 'projection': 'projection.json', 'requirements': 'requirements.json', 'questions': 'questions.json', 'answers': 'answers.json', 'resume_source': 'resume.md', 'resume_claims': 'resume-claims.json', 'cover_letter_source': 'cover-letter.md', 'cover_letter_claims': 'cover-letter-claims.json', 'policy': merged_policy}
    created = False
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.mkdir()
        created = True
        (destination / 'job.txt').write_bytes(raw)
        atomic_write_json(destination / 'projection.json', projection)
        for field in ('requirements', 'questions', 'answers'):
            atomic_write_json(destination / (field + '.json'), {'schema_version': 1, field: []})
        atomic_write_json(destination / 'application.json', record)
    except (OSError, ToolkitError):
        if created:
            shutil.rmtree(destination)
        raise ToolkitError('cannot create application') from None
    return destination
