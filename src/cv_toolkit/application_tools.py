"""Reusable application previews and selected-file freshness, never approval."""
from datetime import datetime, timezone
from hashlib import sha256
from importlib.resources import files
import os
from pathlib import Path
import re
import tempfile

from . import ats, letter_check, render
from .application import load_application
from .deployment import _git, _ignore_check
from .evidence import build_source_registry, load_evidence
from .questions import load_questions, pending_questions
from .records import ToolkitError, atomic_write_json, confined, load_json, nonempty, object_fields, schema
from .workspace import Workspace


def _relative(workspace, path):
    return path.relative_to(workspace.root).as_posix()


def application_context(workspace, application):
    """Inspect standard records without mutating them or drafting any prose."""
    root = confined(workspace.root, application)
    root.relative_to(workspace.applications_dir)
    evidence_path = workspace.profile_dir / 'evidence.json'
    registry_path = workspace.profile_dir / 'registry.json'
    registry = build_source_registry(load_json(confined(workspace.root, _relative(workspace, registry_path))))
    evidence = load_evidence(confined(workspace.root, _relative(workspace, evidence_path)), registry)
    record = load_application(root, evidence, registry)
    inputs = {'configuration': 'cvtool.toml', 'evidence': _relative(workspace, evidence_path),
              'registry': _relative(workspace, registry_path),
              'application': _relative(workspace, root / 'application.json')}
    for field in ('job_source', 'projection', 'requirements', 'questions', 'answers'):
        inputs[field] = _relative(workspace, confined(root, record[field]))
    for kind in record['policy']['deliverables']:
        inputs[kind + '_source'] = _relative(workspace, confined(root, record[kind + '_source'], required=False))
    questions = load_questions(root / record['questions'], evidence, registry)
    requirements = load_json(root / record['requirements'])['requirements']
    return {'application': _relative(workspace, root), 'inputs': inputs,
            'policy': record['policy'], 'extraction_complete': record['extraction_complete'],
            'pending_questions': [q['id'] for q in pending_questions(questions)],
            'requirement_gaps': [{'id': r['id'], 'status': r['status']} for r in requirements
                                 if r['status'] != 'confirmed'],
            'review_status': 'unreviewed_preview', 'release_available': False}


def _package_inputs():
    package = files('cv_toolkit')
    entries = {p.name: p.read_bytes() for p in package.iterdir() if p.name.endswith('.py')}
    assets = package.joinpath('assets')
    for path in assets.iterdir():
        if path.name.endswith(('.css', '.html')):
            entries['assets/' + path.name] = path.read_bytes()
    def skills(directory, prefix):
        for path in directory.iterdir():
            relative = prefix + '/' + path.name
            if path.is_dir():
                skills(path, relative)
            elif path.name.endswith('.md'):
                entries[relative] = path.read_bytes()
    skills(assets.joinpath('skills'), 'assets/skills')
    return entries


def _digest(raw):
    return sha256(raw).hexdigest()


def _output(workspace, relative):
    output = confined(workspace.root, relative, required=False)
    output.relative_to(workspace.outputs_dir)
    if output == workspace.outputs_dir or output.exists():
        raise ToolkitError('bundle destination must be a new directory under outputs')
    discovery = _git(workspace.root, 'rev-parse', '--show-toplevel')
    if discovery is None:
        raise ToolkitError('Git unavailable for output ignore verification')
    if discovery.returncode == 0:
        check = _ignore_check(workspace, discovery.stdout.decode('utf-8').strip())
        if not check['enforced']:
            raise ToolkitError('output ignore verification failed')
        # Check the actual destination too: a nested negation can exempt it.
        probes = [str(output), str(output / 'bundle.json'), str(output / 'inputs/probe')]
        results = [_git(workspace.root, 'check-ignore', '-q', '--', p) for p in probes]
        if any(result is None or result.returncode != 0 for result in results):
            raise ToolkitError('bundle destination is not ignored')
    else:
        # Distinguish a standalone directory from a broken/untrusted repository.
        if any((p / '.git').exists() for p in (workspace.root, *workspace.root.parents)):
            raise ToolkitError('Git repository could not be verified')
        check = _ignore_check(workspace, None)
        if not check['rule_present']:
            raise ToolkitError('configured output directory needs an ignore rule')
    return output, check


def build_application(workspace, application, output, *, output_format='both',
                      styles=('ats', 'branded'), includes=(), page_images=False):
    """Build one immutable preview revision from agent-authored source files.

    Failed document checks are retained for diagnosis and return failure status.
    Operational/render failures publish no partial revision. No external upload.
    """
    if output_format not in {'html', 'both'} or not styles or len(set(styles)) != len(styles) or any(s not in render.RESUME_STYLES for s in styles):
        raise ToolkitError('invalid bundle rendering options')
    if page_images and output_format != 'both':
        raise ToolkitError('page images require PDF output')
    image_module = None
    if page_images:
        try:
            import pymupdf as image_module
        except ImportError:
            raise ToolkitError('page images require the visual extra') from None
    context = application_context(workspace, application)
    if not context['extraction_complete'] or context['pending_questions']:
        raise ToolkitError('application extraction or material questions are incomplete')
    if context['policy']['ai_use'] != 'allowed':
        raise ToolkitError('automated build requires an allowed AI policy; resolve restrictions with the host')
    destination, ignore = _output(workspace, output)
    selected = set(context['inputs'].values()) | set(includes)
    # Read exact inputs once, then render their frozen copies, not moving sources.
    snapshots = {_relative(workspace, confined(workspace.root, p)): confined(workspace.root, p).read_bytes()
                 for p in sorted(selected)}
    package = _package_inputs()
    identity = {'display_name': workspace.display_name, 'email': workspace.email,
                'phone_pattern': workspace.phone_pattern}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.cv-build-', dir=destination.parent,
                                     ignore_cleanup_errors=True) as temporary:
        staging = Path(temporary) / 'revision'
        staging.mkdir()
        for relative, raw in snapshots.items():
            target = staging / 'inputs' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        # Validate the exact copies, not a context read before the snapshot.
        # This also catches edits during the Git checks between those operations.
        frozen_workspace = Workspace.load(staging / 'inputs')
        if application_context(frozen_workspace, context['application']) != context:
            raise ToolkitError('application changed before snapshot')
        if (frozen_workspace.display_name, frozen_workspace.email, frozen_workspace.phone_pattern) != (workspace.display_name, workspace.email, workspace.phone_pattern):
            raise ToolkitError('workspace identity changed before snapshot')
        checks = {}
        documents = []
        for kind in context['policy']['deliverables']:
            source = staging / 'inputs' / context['inputs'][kind + '_source']
            checker = ats.check if kind == 'resume' else letter_check.check
            for style in (styles if kind == 'resume' else ('letter',)):
                name = 'resume-' + style if kind == 'resume' else 'cover-letter'
                html = staging / (name + '.html')
                html.write_bytes(render.render_html(source.read_text(encoding='utf-8'), style, kind).encode('utf-8'))
                paths = [html]
                if output_format == 'both':
                    pdf = staging / (name + '.pdf')
                    render.render_pdf(source, pdf, style, kind)
                    paths.append(pdf)
                    if image_module is not None:
                        with image_module.open(pdf) as document:
                            for number, page in enumerate(document, 1):
                                page.get_pixmap(matrix=image_module.Matrix(1.5, 1.5)).save(
                                    str(staging / f'{name}-page-{number}.png'))
                for path in paths:
                    checks[path.name] = checker(path, identity, policy=context['policy'])
                    documents.append(path.name)
        atomic_write_json(staging / 'checks.json', checks)
        packet = ('# Application review packet\n\n'
                  'Status: unreviewed preview. No submission or release approval.\n\n'
                  'Read the frozen files under `inputs/` and the manifest `context`. '
                  'Inspect every PDF page and all check observations. Delegate actual independent reviews.\n\n'
                  'Source coverage: not assessed automatically. Extra inputs are explicitly selected by the host; '
                  'follow claim/support references to original sources and prior answers. Registry fingerprints '
                  'alone do not establish source freshness. Missing dependencies must be disclosed and included '
                  'in a new revision. Hashes do not authenticate reviewers or prevent manifest tampering.\n\n'
                  'Before review and handoff run `cv verify-bundle --workspace ROOT --bundle '
                  + _relative(workspace, destination / 'bundle.json') + '`.\n\n'
                  'Documents:\n' + ''.join('- ' + name + '\n' for name in documents) + '\n'
                  'Page images: ' + ('generated; still require visual inspection' if page_images else 'not generated') + '.\n')
        (staging / 'review-packet.md').write_bytes(packet.encode('utf-8'))
        # A change during rendering must not leave apparently current artifacts.
        if any(confined(workspace.root, p).read_bytes() != raw for p, raw in snapshots.items()) or _package_inputs() != package:
            raise ToolkitError('inputs changed during build')
        artifacts = {p.relative_to(staging).as_posix(): _digest(p.read_bytes())
                     for p in staging.rglob('*') if p.is_file()}
        failed = any(check['status'] == 'fail' for check in checks.values())
        manifest = {'schema_version': 1, 'context': context,
                    'output': _relative(workspace, destination),
                    'workspace_inputs': {p: _digest(raw) for p, raw in snapshots.items()},
                    'package_inputs': {p: _digest(raw) for p, raw in package.items()},
                    'artifacts': artifacts, 'documents': documents,
                    'checks_status': 'failed' if failed else 'passed',
                    'page_images': page_images, 'output_ignore': ignore,
                    'review_status': 'unreviewed_preview', 'release_available': False}
        atomic_write_json(staging / 'bundle.json', manifest)
        if ignore['enforced']:
            # Test every actual destination, including copied source files, against
            # nested ignore exceptions before publishing any part of the revision.
            targets = [(destination / p).as_posix() for p in (*artifacts, 'bundle.json')]
            result = _git(workspace.root, 'check-ignore', '-z', '--stdin',
                          input=('\0'.join(targets) + '\0').encode('utf-8'))
            if result is None or result.returncode != 0 or set(result.stdout.decode('utf-8').split('\0')) - {''} != set(targets):
                raise ToolkitError('one or more bundle files are not ignored')
        if destination.exists():
            raise ToolkitError('bundle destination already exists')
        os.rename(staging, destination)
    return {'status': 'failed' if failed else 'ok', 'bundle': _relative(workspace, destination / 'bundle.json'),
            'review_status': 'unreviewed_preview', 'release_available': False,
            'checks_status': manifest['checks_status'], 'documents': documents}


def verify_bundle(workspace, bundle):
    """Compare selected input and output bytes; not semantic completeness or approval."""
    path = confined(workspace.root, bundle)
    path.relative_to(workspace.outputs_dir)
    record = load_json(path)
    object_fields(record, {'schema_version', 'context', 'output', 'workspace_inputs', 'package_inputs',
                          'artifacts', 'documents', 'checks_status', 'page_images', 'output_ignore',
                          'review_status', 'release_available'}, rule='bundle')
    schema(record['schema_version'])
    if confined(workspace.root, record['output']) != path.parent or path.name != 'bundle.json':
        raise ToolkitError('bundle location mismatch')
    if record['review_status'] != 'unreviewed_preview' or record['release_available'] is not False:
        raise ToolkitError('bundle cannot declare approval')
    if record['checks_status'] not in ('passed', 'failed') or type(record['page_images']) is not bool:
        raise ToolkitError('invalid bundle status')
    context = record['context']
    if not isinstance(context, dict) or not isinstance(context.get('inputs'), dict):
        raise ToolkitError('missing bundle context')
    if not context['inputs'] or any(not isinstance(p, str) or not p.strip() for p in context['inputs'].values()):
        raise ToolkitError('invalid context input paths')
    required = {'cvtool.toml', _relative(workspace, workspace.profile_dir / 'evidence.json'),
                _relative(workspace, workspace.profile_dir / 'registry.json')}
    if not isinstance(record['workspace_inputs'], dict) or not required <= record['workspace_inputs'].keys():
        raise ToolkitError('missing mandatory profile dependencies')
    if not set(context['inputs'].values()) <= record['workspace_inputs'].keys():
        raise ToolkitError('missing application dependencies')
    if not isinstance(record['artifacts'], dict) or not {'checks.json', 'review-packet.md'} <= record['artifacts'].keys():
        raise ToolkitError('missing bundle artifacts')
    if not isinstance(record['documents'], list) or not record['documents'] or any(not isinstance(p, str) or p not in record['artifacts'] for p in record['documents']):
        raise ToolkitError('missing bundle documents')
    if any('inputs/' + p not in record['artifacts'] for p in record['workspace_inputs']):
        raise ToolkitError('missing input snapshots')
    changed, missing = [], []
    package = _package_inputs()
    for field, base in (('workspace_inputs', workspace.root), ('artifacts', path.parent), ('package_inputs', None)):
        entries = record[field]
        if not isinstance(entries, dict) or not entries:
            raise ToolkitError('missing bundle dependencies')
        for relative, expected in entries.items():
            if not isinstance(expected, str) or not re.fullmatch(r'[a-f0-9]{64}', expected):
                raise ToolkitError('invalid dependency fingerprint')
            label = ('package:' + relative if base is None else
                     _relative(workspace, path.parent / relative) if field == 'artifacts' else relative)
            if base is None:
                raw = package.get(relative)
            else:
                candidate = confined(base, relative, required=False)
                raw = candidate.read_bytes() if candidate.is_file() else None
            if raw is None:
                missing.append(label)
            elif _digest(raw) != expected:
                changed.append(label)
    if set(package) != set(record['package_inputs']):
        changed.append('package:inventory')
    fresh = not changed and not missing
    return {'status': 'ok' if fresh else 'failed', 'freshness': 'fresh' if fresh else 'stale',
            'changed': changed, 'missing': missing, 'source_coverage': 'host_selected_not_authenticated',
            'checks_status': record['checks_status'], 'review_status': 'unreviewed_preview',
            'release_available': False}


ANGLES = {'resume': ('factual', 'alignment', 'voice', 'visual'),
          'cover_letter': ('factual', 'persuasiveness', 'motivation', 'voice', 'visual')}
VERDICTS = ('pass', 'findings', 'unavailable')


def _reviewed_bundle(workspace, bundle):
    verify_bundle(workspace, bundle)  # structural validation; staleness is reported per angle
    path = confined(workspace.root, bundle)
    return path, load_json(path)


def _document_hashes(path, record, kind):
    prefix = 'resume-' if kind == 'resume' else 'cover-letter'
    return {name: _digest((path.parent / name).read_bytes()) if (path.parent / name).is_file() else None
            for name in record['documents'] if name.startswith(prefix)}


def _reviews(path):
    ledger = path.parent / 'reviews.json'
    if not ledger.exists():
        return []
    record = load_json(ledger)
    object_fields(record, {'schema_version', 'reviews'}, rule='review ledger')
    schema(record['schema_version'])
    if not isinstance(record['reviews'], list):
        raise ToolkitError('invalid review ledger')
    for entry in record['reviews']:
        object_fields(entry, {'document', 'angle', 'verdict', 'bundle_sha256', 'artifacts', 'recorded_at'},
                      {'findings', 'reviewer'}, rule='review entry')
    return record['reviews']


def record_review(workspace, bundle, document, angle, verdict, findings=None, reviewer=None):
    """Append one declared verdict; it authenticates no reviewer and approves nothing."""
    path, record = _reviewed_bundle(workspace, bundle)
    if document not in record['context']['policy']['deliverables'] or angle not in ANGLES[document] \
            or verdict not in VERDICTS:
        raise ToolkitError('invalid review angle or verdict')
    if (verdict == 'findings') != (findings is not None):
        raise ToolkitError('a findings verdict needs a findings file, and only it')
    entry = {'document': document, 'angle': angle, 'verdict': verdict,
             'bundle_sha256': _digest(path.read_bytes()),
             'artifacts': _document_hashes(path, record, document),
             'recorded_at': datetime.now(timezone.utc).isoformat()}
    if findings is not None:
        report = confined(workspace.root, findings)
        report.relative_to(workspace.outputs_dir)
        if not report.is_file():
            raise ToolkitError('findings file missing')
        entry['findings'] = _relative(workspace, report)
    if reviewer is not None:
        entry['reviewer'] = nonempty(reviewer, 'reviewer').strip()
    atomic_write_json(path.parent / 'reviews.json',
                      {'schema_version': 1, 'reviews': [*_reviews(path), entry]})
    return review_status(workspace, bundle)


def review_status(workspace, bundle):
    """Which required review angles have a current declared verdict; never an approval."""
    path, record = _reviewed_bundle(workspace, bundle)
    latest = {(e['document'], e['angle']): e for e in _reviews(path)}
    angles = {}
    for document in record['context']['policy']['deliverables']:
        current = _document_hashes(path, record, document)
        for angle in ANGLES[document]:
            entry = latest.get((document, angle))
            state = ('missing' if entry is None else 'stale' if entry['artifacts'] != current
                     else 'unavailable' if entry['verdict'] == 'unavailable' else 'recorded')
            angles[document + '.' + angle] = {'state': state, 'verdict': entry and entry['verdict']}
    by_state = {s: [a for a, v in angles.items() if v['state'] == s]
                for s in ('missing', 'stale', 'unavailable')}
    return {'angles': angles, **by_state,
            'coverage': 'complete' if all(v['state'] == 'recorded' for v in angles.values()) else 'incomplete',
            'review_status': 'unreviewed_preview', 'release_available': False}
