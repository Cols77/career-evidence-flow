"""Ordered selections of publishable evidence; never edits canonical evidence."""
from .evidence import EvidenceError, publishable_claims
from .records import ToolkitError, identifier, identifiers, load_json, nonempty, object_fields, schema


def evidence_claims(evidence, registry):
    try:
        return publishable_claims(evidence, registry)
    except EvidenceError as exc:
        raise ToolkitError(str(exc)) from None


def selected_claims(value, claims, rule, *, required=False):
    identifiers(value, rule, nonempty_list=required)
    if claims is not None and any(claim_id not in claims for claim_id in value):
        raise ToolkitError('unpublishable or dangling claim reference')
    return value


def _validate_projection(record, claims=None, items=None, ownership=None):
    object_fields(record, {'schema_version', 'id', 'label', 'sections'}, {'headline', 'skills', 'summary_claim_ids'}, rule='projection')
    schema(record['schema_version'])
    identifier(record['id'], 'projection id')
    nonempty(record['label'], 'projection label')
    if 'headline' in record:
        nonempty(record['headline'], 'projection headline')
    if not isinstance(record['sections'], list):
        raise ToolkitError('invalid projection sections')
    seen_sections, seen_items, seen_claims = set(), set(), set()
    for section in record['sections']:
        object_fields(section, {'id', 'label', 'item_ids', 'claim_ids'}, rule='section')
        section_id = identifier(section['id'], 'section id')
        if section_id in seen_sections:
            raise ToolkitError('duplicate section id')
        seen_sections.add(section_id)
        nonempty(section['label'], 'section label')
        identifiers(section['item_ids'], 'section item ids')
        selected_claims(section['claim_ids'], claims, 'section claim ids')
        if items is not None and any(item_id not in items for item_id in section['item_ids']):
            raise ToolkitError('dangling item reference')
        if seen_items.intersection(section['item_ids']) or seen_claims.intersection(section['claim_ids']):
            raise ToolkitError('duplicate section selection')
        if ownership is not None and any(ownership[claim_id] not in section['item_ids'] for claim_id in section['claim_ids']):
            raise ToolkitError('claim does not belong to selected item')
        if ownership is not None and any(not any(ownership[claim_id] == item_id for claim_id in section['claim_ids']) for item_id in section['item_ids']):
            raise ToolkitError('selected item has no selected claims')
        seen_items.update(section['item_ids'])
        seen_claims.update(section['claim_ids'])
    if 'skills' in record:
        if not isinstance(record['skills'], list):
            raise ToolkitError('invalid projection skills')
        names = set()
        for skill in record['skills']:
            object_fields(skill, {'name', 'claim_ids'}, rule='skill')
            name = nonempty(skill['name'], 'skill name')
            if name.casefold() in names:
                raise ToolkitError('duplicate skill name')
            names.add(name.casefold())
            selected_claims(skill['claim_ids'], claims, 'skill claim ids', required=True)
    if 'summary_claim_ids' in record:
        selected_claims(record['summary_claim_ids'], claims, 'summary claim ids')
    return record


def validate_projection_structure(record):
    """Validate layout syntax only; canonical evidence validation remains required."""
    return _validate_projection(record)


def validate_projection(record, evidence, registry):
    claims = evidence_claims(evidence, registry)
    items = {item['id']: item for item in evidence['items']}
    ownership = {claim['id']: item['id'] for item in evidence['items'] for claim in item['claims']}
    return _validate_projection(record, claims, items, ownership)


def load_projection(path, evidence, registry):
    return validate_projection(load_json(path), evidence, registry)
