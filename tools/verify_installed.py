"""Run with a wheel-installed interpreter from outside the source checkout.

Produces unreviewed synthetic preview artifacts, never production approvals.
Requires locally installed Chrome/Chromium for the sequential PDF matrix.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-checkout', type=Path, required=True)
    args = parser.parse_args(argv)
    import cv_toolkit
    from cv_toolkit import ats, letter_check
    from cv_toolkit.render import RESUME_STYLES, render_pdf

    imported = Path(cv_toolkit.__file__).resolve()
    assert not imported.is_relative_to(args.source_checkout.resolve()), 'source checkout import'
    assert imported.is_relative_to(Path(sys.prefix).resolve()), 'package is not in this environment'
    assert not Path.cwd().resolve().is_relative_to(args.source_checkout.resolve()), 'run from outside the checkout'
    args.output = args.output.resolve()
    assert not args.output.is_relative_to(args.source_checkout.resolve()), 'acceptance output must be outside the checkout'
    assert (Path(sys.prefix) / 'Scripts/cv.exe').is_file() if sys.platform == 'win32' else (Path(sys.prefix) / 'bin/cv').is_file()
    executable = Path(sys.prefix) / ('Scripts/cv.exe' if sys.platform == 'win32' else 'bin/cv')
    args.output.mkdir(parents=True, exist_ok=False)
    report = {'status': 'ok', 'version': cv_toolkit.__version__, 'installed_package': str(imported),
              'deployments': [], 'profiles': [], 'pdf_checks': [],
              'host_runtime_discovery': 'unverified', 'review_status': 'unreviewed_preview'}

    def command(*parts):
        result = subprocess.run([str(executable), *parts], cwd=args.output, capture_output=True, text=True)
        assert result.returncode == 0, f'installed console command failed: {parts}\n{result.stdout}\n{result.stderr}'
        record = json.loads(result.stdout)
        assert record['status'] == 'ok'
        return record

    def snapshot(root):
        return {path.relative_to(root).as_posix():
                (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
                for path in root.rglob('*') if path.is_file()}

    prefixes = {'codex': '.agents/skills', 'claude': '.claude/skills', 'hermes': '.hermes/skills'}
    for host in (*prefixes, 'all'):
        root = args.output / f'setup-{host}'
        first = command('setup', str(root), '--host', host)
        selected = set(prefixes) if host == 'all' else {host}
        assert first['initialized'] is True and first['runtime_discovery_verified'] is False
        assert first['hooks_changed'] is False and first['hooks_installed_by_setup'] is False
        assert set(first['hosts']) == selected
        for item, prefix in prefixes.items():
            assert (root / prefix).is_dir() == (item in selected), 'setup installed an unrequested host'
        before = snapshot(root)
        repeated = command('setup', str(root), '--host', host)
        assert repeated['initialized'] is False and repeated['profile_preserved'] is True
        assert all(entry['skills'] == 'unchanged' for entry in repeated['hosts'].values())
        diagnosis = command('doctor', '--workspace', str(root), '--host', host)
        assert diagnosis['runtime_discovery_verified'] is False
        assert diagnosis['hook_execution_verified'] is False
        assert diagnosis['independent_review_verified'] is False
        assert snapshot(root) == before, 'setup repeat or doctor changed existing workspace files'
        for item in selected:
            assert any(check['id'] == f'skills.{item}' and check['status'] == 'pass'
                       for check in diagnosis['checks'])
        report['deployments'].append({'host': host, 'repeat_setup': 'unchanged',
                                      'doctor_read_only': True, 'diagnostics': diagnosis['checks']})

    for profile in ('developer', 'researcher'):
        root = args.output / profile
        command('init', str(root), '--example', profile)
        command('validate-evidence', '--workspace', str(root))
        command('validate-projection', '--workspace', str(root))
        for host in ('codex', 'claude', 'hermes'):
            record = command('install-skills', '--workspace', str(root), '--host', host)
            assert record['skill_count'] == 4
            assert record['runtime_discovery_verified'] is False
            prefix = prefixes[host]
            for skill in ('experience-capture', 'application-materials', 'resume-review', 'cover-letter-review'):
                folder = root / prefix / skill
                pages = list(folder.rglob('*.md'))
                assert len(pages) >= 2, 'installed skill references missing'
                for page in pages:
                    for link in re.findall(r'\]\(([^)]+)\)', page.read_text(encoding='utf-8')):
                        if '://' not in link and not link.startswith('#'):
                            target = (page.parent / link.split('#')[0]).resolve()
                            assert target.is_relative_to(root) and target.is_file(), 'broken installed skill reference'
        # Upgrade a populated workspace created through the existing init/install
        # commands, then rerun setup without changing evidence or instructions.
        profile_before = snapshot(root / 'profile')
        command('setup', str(root), '--host', 'all')
        assert snapshot(root / 'profile') == profile_before, 'setup replaced existing synthetic profile'
        before = snapshot(root)
        conflicting = subprocess.run([str(executable), 'setup', str(root), '--host', 'all', '--example', 'showcase'],
                                     cwd=args.output, capture_output=True, text=True)
        assert conflicting.returncode != 0, 'setup accepted a replacement example for an existing profile'
        assert snapshot(root) == before, 'rejected example replacement changed the workspace'
        command('setup', str(root), '--host', 'all')
        command('doctor', '--workspace', str(root), '--host', 'all')
        assert snapshot(root) == before, 'existing workspace initialization is not idempotent'
        for kind, source, styles in [('resume', 'resume.md', RESUME_STYLES), ('cover_letter', 'letter.md', ('letter',))]:
            for style in styles:
                relative = f'outputs/{kind}-{style}.html'
                command('render', '--workspace', str(root), '--source', source, '--output', relative, '--kind', kind, '--style', style)
                command('check', '--workspace', str(root), '--document', relative, '--kind', kind)
                pdf = root / 'outputs' / f'{kind}-{style}.pdf'
                render_pdf(root / source, pdf, style=style, document_kind=kind)
                from cv_toolkit.workspace import Workspace
                ws = Workspace.load(root)
                checker = ats.check if kind == 'resume' else letter_check.check
                from cv_toolkit.application import DEFAULT_POLICY
                check = checker(pdf, {'display_name': ws.display_name, 'email': ws.email}, DEFAULT_POLICY)
                assert check['status'] == 'pass', 'installed PDF check failed'
                report['pdf_checks'].append({'profile': profile, 'kind': kind, 'style': style, 'pages': check['pages'], 'status': 'pass'})
        raw_job = b'Supplied full job description\r\nPython experience preferred.\r\n'
        (root / 'job.txt').write_bytes(raw_job)
        command('create-application', '--workspace', str(root), '--slug', 'synthetic-role', '--job', 'job.txt', '--company', 'Example Organization', '--title', 'Example role')
        assert (root / 'applications/synthetic-role/job.txt').read_bytes() == raw_job
        state = command('status', '--workspace', str(root), '--application', 'applications/synthetic-role')
        assert state['readiness'] == 'draft_only' and state['release_available'] is False
        report['profiles'].append(profile)
    gallery = args.output / 'visual-gallery'
    command('gallery', '--output', str(gallery), '--format', 'both')
    report['gallery_checks'] = json.loads((gallery / 'checks.json').read_text(encoding='utf-8'))
    assert set(report['gallery_checks']) == set(RESUME_STYLES)
    assert all(check['pdf']['pages'] == 2 and check['pdf_matches_html']
               for check in report['gallery_checks'].values()), 'gallery content or pagination changed'
    (args.output / 'installed-results.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
