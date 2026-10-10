"""Generic offline workspace tools. Validation is not semantic approval."""
import argparse
import json
import os
from pathlib import Path
import tempfile

from .bootstrap import init_workspace, install_skills
from .evidence import build_source_registry, claim_index, load_evidence
from .records import ToolkitError, confined, load_json
from .workspace import Workspace


def _atomic_text(path, text):
    raw = text.encode('utf-8')
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.preview-', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _profile_path(workspace, filename):
    return workspace.profile_dir.relative_to(workspace.root).joinpath(filename).as_posix()


def _profile(workspace, evidence=None, registry=None):
    evidence = evidence or _profile_path(workspace, 'evidence.json')
    registry = registry or _profile_path(workspace, 'registry.json')
    sources = build_source_registry(load_json(confined(workspace.root, registry)))
    record = load_evidence(confined(workspace.root, evidence), sources)
    return record, sources


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init', help='Create an empty private workspace or a synthetic example')
    init.add_argument('directory', type=Path)
    init.add_argument('--name', default='Candidate')
    init.add_argument('--example', choices=('developer', 'researcher'))
    for command in ('validate-evidence', 'validate-projection', 'render', 'check', 'install-skills', 'create-application', 'status', 'answer', 'resolve-question'):
        item = sub.add_parser(command)
        item.add_argument('--workspace', type=Path, required=True)
        if command in {'validate-evidence', 'validate-projection', 'create-application', 'status', 'answer', 'resolve-question'}:
            item.add_argument('--evidence')
            item.add_argument('--registry')
        if command in {'validate-projection', 'create-application'}:
            item.add_argument('--projection')
        if command == 'render':
            item.add_argument('--source', required=True)
            item.add_argument('--output', required=True)
            item.add_argument('--format', choices=('html', 'pdf'), default='html')
            item.add_argument('--style', choices=('ats', 'branded', 'letter'), default='ats')
            item.add_argument('--kind', choices=('resume', 'cover_letter'), default='resume')
        if command == 'check':
            item.add_argument('--document', required=True)
            item.add_argument('--kind', choices=('resume', 'cover_letter'), default='resume')
            item.add_argument('--policy', help='Workspace-relative effective policy JSON')
        if command == 'install-skills':
            item.add_argument('--host', choices=('codex', 'claude', 'hermes'), required=True)
        if command == 'create-application':
            item.add_argument('--slug', required=True)
            item.add_argument('--job', required=True, help='Workspace-relative full supplied job text file')
            item.add_argument('--company', required=True)
            item.add_argument('--title', required=True)
            item.add_argument('--policy')
        if command == 'status':
            item.add_argument('--application', required=True, help='Workspace-relative application directory')
        if command in {'answer', 'resolve-question'}:
            item.add_argument('--questions', required=True)
            item.add_argument('--question-id', required=True)
        if command == 'answer':
            item.add_argument('--text', required=True)
            item.add_argument('--source-id', required=True)
            item.add_argument('--recorded-at', required=True)
            item.add_argument('--correction', action='store_true')
        if command == 'resolve-question':
            item.add_argument('--resolution', required=True, help='Workspace-relative supplied resolution JSON')
            item.add_argument('--status', choices=('resolved', 'unknown', 'declined', 'not_needed'), default='resolved')
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    result = {'command': args.command, 'status': 'ok'}
    try:
        if args.command == 'init':
            init_workspace(args.directory, name=args.name, example=args.example)
            result['synthetic'] = args.example is not None
        else:
            ws = Workspace.load(args.workspace)
            if args.command == 'validate-evidence':
                record, registry = _profile(ws, args.evidence, args.registry)
                result['claim_count'] = len(claim_index(record, registry))
            elif args.command == 'validate-projection':
                from .projection import load_projection
                evidence, registry = _profile(ws, args.evidence, args.registry)
                record = load_projection(confined(ws.root, args.projection or _profile_path(ws, 'projection.json')), evidence, registry)
                result['section_count'] = len(record['sections'])
            elif args.command == 'install-skills':
                result['skill_count'] = install_skills(ws.root, args.host)
                result['runtime_discovery_verified'] = False
            elif args.command == 'render':
                from .render import render_html, render_pdf
                source = confined(ws.root, args.source)
                output = confined(ws.root, args.output, required=False)
                if source == output:
                    raise ToolkitError('source and output must differ')
                if output.suffix.lower() != '.' + args.format:
                    raise ToolkitError('output format mismatch')
                if args.format == 'html':
                    html = render_html(source.read_text(encoding='utf-8'), style=args.style, document_kind=args.kind)
                    _atomic_text(output, html)
                else:
                    render_pdf(source, output, style=args.style, document_kind=args.kind)
                result['review_status'] = 'unreviewed_preview'
            elif args.command == 'check':
                from . import ats, letter_check
                from .application import DEFAULT_POLICY
                policy = load_json(confined(ws.root, args.policy)) if args.policy else DEFAULT_POLICY
                candidate = {'display_name': ws.display_name, 'email': ws.email, 'phone_pattern': ws.phone_pattern}
                checker = ats.check if args.kind == 'resume' else letter_check.check
                result['checks'] = checker(confined(ws.root, args.document), candidate, policy=policy)
                if result['checks']['status'] == 'fail':
                    result['status'] = 'failed'
            elif args.command == 'create-application':
                from .application import create_application
                from .projection import load_projection
                evidence, registry = _profile(ws, args.evidence, args.registry)
                projection_path = args.projection or _profile_path(ws, 'projection.json')
                load_projection(confined(ws.root, projection_path), evidence, registry)
                job = confined(ws.root, args.job).read_bytes().decode('utf-8')
                policy = load_json(confined(ws.root, args.policy)) if args.policy else None
                create_application(ws, args.slug, job, args.company, args.title, projection_path, policy)
                result['extraction_complete'] = False
            elif args.command == 'status':
                from .application import load_application
                from .questions import load_questions, pending_questions
                evidence, registry = _profile(ws, args.evidence, args.registry)
                root = confined(ws.root, args.application)
                application = load_application(root, evidence, registry)
                result.update(readiness='draft_only', extraction_complete=application['extraction_complete'], pending_question_count=len(pending_questions(load_questions(confined(root, application['questions']), evidence, registry))), release_available=False)
            elif args.command == 'answer':
                from .questions import load_questions, record_answer
                evidence, registry = _profile(ws, args.evidence, args.registry)
                load_questions(confined(ws.root, args.questions), evidence, registry)
                if args.source_id not in registry:
                    raise ToolkitError('unknown answer source')
                record_answer(confined(ws.root, args.questions), args.question_id, args.text, args.source_id, args.recorded_at, correction=args.correction)
            elif args.command == 'resolve-question':
                from .questions import resolve_question
                evidence, registry = _profile(ws, args.evidence, args.registry)
                resolve_question(confined(ws.root, args.questions), args.question_id, load_json(confined(ws.root, args.resolution)), evidence, registry, status=args.status)
    except (ValueError, OSError, RuntimeError, RecursionError, OverflowError):
        result = {'command': args.command, 'status': 'invalid', 'error': 'validation or local operation failed'}
    print(json.dumps(result, sort_keys=True, separators=(',', ':')))
    return 0 if result['status'] == 'ok' else 2


if __name__ == '__main__':
    raise SystemExit(main())
