"""Reusable application mechanics exercised only with fictional candidates."""
import json
import shutil
import subprocess
import sys

import pytest

from cv_toolkit.cli import main


@pytest.fixture
def application(tmp_path, capsys):
    root = tmp_path / 'workspace'
    assert main(['init', str(root), '--example', 'developer']) == 0
    (root / 'job.txt').write_text('Build reliable Python services.', encoding='utf-8')
    assert main(['create-application', '--workspace', str(root), '--slug', 'example',
                 '--job', 'job.txt', '--company', 'Example', '--title', 'Engineer']) == 0
    app = root / 'applications/example'
    record = json.loads((app / 'application.json').read_text())
    record['extraction_complete'] = True
    (app / 'application.json').write_text(json.dumps(record), encoding='utf-8')
    shutil.copyfile(root / 'resume.md', app / 'resume.md')
    shutil.copyfile(root / 'letter.md', app / 'cover-letter.md')
    capsys.readouterr()
    return root, app


def invoke(capsys, root, command, *args):
    try:
        code = main([command, '--workspace', str(root), *args])
    except SystemExit as error:
        pytest.fail(f'Reusable command unavailable: {error}')
    return code, json.loads(capsys.readouterr().out)


def build(capsys, root, *args):
    return invoke(capsys, root, 'build-application', '--application', 'applications/example',
                  '--output', 'outputs/example/r01', '--format', 'html', *args)


def test_context_inspects_without_generating_documents(application, capsys):
    root, _ = application
    code, result = invoke(capsys, root, 'application-context', '--application', 'applications/example')
    assert code == 0
    assert result['policy']['deliverables'] == ['resume', 'cover_letter']
    assert result['pending_questions'] == []
    assert result['inputs']['evidence'] == 'profile/evidence.json'
    assert not list((root / 'outputs').iterdir())


def test_build_and_verify_complete_html_bundle(application, capsys):
    root, _ = application
    (root / 'prior-answer.txt').write_text('Fictional source answer', encoding='utf-8')
    code, result = build(capsys, root, '--include', 'prior-answer.txt')
    assert code == 0
    assert result['review_status'] == 'unreviewed_preview'
    output = root / 'outputs/example/r01'
    for name in ('resume-ats.html', 'resume-branded.html', 'cover-letter.html',
                 'checks.json', 'bundle.json', 'review-packet.md'):
        assert (output / name).is_file()
    code, verified = invoke(capsys, root, 'verify-bundle', '--bundle', 'outputs/example/r01/bundle.json')
    assert code == 0
    assert verified['freshness'] == 'fresh'
    assert verified['release_available'] is False
    (root / 'prior-answer.txt').write_text('Corrected answer', encoding='utf-8')
    code, verified = invoke(capsys, root, 'verify-bundle', '--bundle', 'outputs/example/r01/bundle.json')
    assert code == 2
    assert verified['freshness'] == 'stale'
    assert 'prior-answer.txt' in verified['changed']


@pytest.mark.parametrize('path', ['applications/example/resume.md', 'profile/evidence.json',
                                   'outputs/example/r01/resume-ats.html'])
def test_changed_and_missing_inputs_stale_bundle(application, capsys, path):
    root, _ = application
    assert build(capsys, root)[0] == 0
    (root / path).unlink()
    code, result = invoke(capsys, root, 'verify-bundle', '--bundle', 'outputs/example/r01/bundle.json')
    assert code == 2 and result['freshness'] == 'stale'
    assert path in result['missing']


def test_build_refuses_existing_revision(application, capsys):
    root, _ = application
    assert build(capsys, root)[0] == 0
    path = root / 'outputs/example/r01/bundle.json'
    original = path.read_bytes()
    assert build(capsys, root)[0] == 2
    assert path.read_bytes() == original


@pytest.mark.parametrize('output', ['../escaped', 'applications/example/generated', 'outputs'])
def test_build_confines_output(application, capsys, output):
    root, _ = application
    assert invoke(capsys, root, 'build-application', '--application', 'applications/example',
                  '--output', output, '--format', 'html')[0] == 2


def test_resume_only_policy_does_not_read_or_render_letter(application, capsys):
    root, app = application
    path = app / 'application.json'
    record = json.loads(path.read_text())
    record['policy']['deliverables'] = ['resume']
    path.write_text(json.dumps(record), encoding='utf-8')
    (app / 'cover-letter.md').unlink()
    assert build(capsys, root)[0] == 0
    assert not (root / 'outputs/example/r01/cover-letter.html').exists()


@pytest.mark.parametrize('policy', ['forbidden', 'restricted'])
def test_non_allowed_ai_policy_requires_host_resolution(application, capsys, policy):
    root, app = application
    path = app / 'application.json'
    record = json.loads(path.read_text())
    record['policy']['ai_use'] = policy
    path.write_text(json.dumps(record), encoding='utf-8')
    assert build(capsys, root)[0] == 2
    assert not (root / 'outputs/example/r01').exists()


def test_failed_document_check_is_preserved_and_returns_failure(application, capsys):
    root, app = application
    (app / 'resume.md').write_text('# Somebody Else\n\nMissing contact data.', encoding='utf-8')
    code, result = build(capsys, root)
    assert code == 2 and result['status'] == 'failed'
    checks = json.loads((root / 'outputs/example/r01/checks.json').read_text())
    assert checks['resume-ats.html']['status'] == 'fail'


def test_render_failure_leaves_no_partial_revision(application, capsys):
    root, app = application
    (app / 'cover-letter.md').write_text('<script>bad</script>', encoding='utf-8')
    assert build(capsys, root)[0] == 2
    assert not (root / 'outputs/example/r01').exists()


def test_output_must_be_ignored_in_git(application, capsys):
    root, _ = application
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    (root / '.gitignore').write_text('', encoding='utf-8')
    assert build(capsys, root)[0] == 2
    assert not (root / 'outputs/example/r01').exists()


def test_ignored_git_workspace_can_build(application, capsys):
    root, _ = application
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    assert build(capsys, root)[0] == 0
    record = json.loads((root / 'outputs/example/r01/bundle.json').read_text())
    assert record['output_ignore']['enforced'] is True


def test_nested_ignore_exception_blocks_publication(application, capsys):
    root, _ = application
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    (root / '.gitignore').write_text('outputs/**\n!outputs/example/\n!outputs/example/r01/\n!outputs/example/r01/resume-ats.html\n', encoding='utf-8')
    assert build(capsys, root)[0] == 2
    assert not (root / 'outputs/example/r01').exists()


def test_inputs_changing_during_render_are_not_published(application, capsys, monkeypatch):
    from cv_toolkit import render
    root, app = application
    original = render.render_html
    def changing_render(*args, **kwargs):
        (app / 'resume.md').write_text('# Changed while rendering', encoding='utf-8')
        return original(*args, **kwargs)
    monkeypatch.setattr(render, 'render_html', changing_render)
    assert build(capsys, root)[0] == 2
    assert not (root / 'outputs/example/r01').exists()


def test_policy_changed_between_validation_and_snapshot_blocks_build(application, capsys, monkeypatch):
    from cv_toolkit import application_tools
    root, app = application
    original = application_tools._output
    def changing_output(*args):
        output = original(*args)
        path = app / 'application.json'
        record = json.loads(path.read_text())
        record['policy']['ai_use'] = 'forbidden'
        path.write_text(json.dumps(record), encoding='utf-8')
        return output
    monkeypatch.setattr(application_tools, '_output', changing_output)
    assert build(capsys, root)[0] == 2
    assert not (root / 'outputs/example/r01').exists()


def test_package_change_stales_existing_bundle(application, capsys, monkeypatch):
    from cv_toolkit import application_tools
    root, _ = application
    assert build(capsys, root)[0] == 0
    package = application_tools._package_inputs()
    package['assets/branded.css'] += b'\n/* new style */'
    monkeypatch.setattr(application_tools, '_package_inputs', lambda: package)
    code, result = invoke(capsys, root, 'verify-bundle', '--bundle', 'outputs/example/r01/bundle.json')
    assert code == 2
    assert 'package:assets/branded.css' in result['changed']


def test_pending_material_question_blocks_build(application, capsys):
    root, app = application
    (app / 'questions.json').write_text(json.dumps({'schema_version': 1, 'questions': [{
        'id': 'question.outcome', 'prompt': 'What was the result?', 'reason': 'Clarify impact', 'material': True,
        'status': 'pending', 'unlocks': []}]}), encoding='utf-8')
    code, context = invoke(capsys, root, 'application-context', '--application', 'applications/example')
    assert code == 0 and context['pending_questions'] == ['question.outcome']
    assert build(capsys, root)[0] == 2
    assert not (root / 'outputs/example/r01').exists()


def test_missing_included_source_is_not_silently_omitted(application, capsys):
    root, _ = application
    assert build(capsys, root, '--include', 'missing-source.txt')[0] == 2
    assert not (root / 'outputs/example/r01').exists()


def test_bundle_manifest_cannot_drop_mandatory_inputs(application, capsys):
    root, _ = application
    assert build(capsys, root)[0] == 0
    path = root / 'outputs/example/r01/bundle.json'
    record = json.loads(path.read_text())
    del record['workspace_inputs']['profile/evidence.json']
    path.write_text(json.dumps(record), encoding='utf-8')
    assert invoke(capsys, root, 'verify-bundle', '--bundle', 'outputs/example/r01/bundle.json')[0] == 2


@pytest.mark.parametrize('mutation', ['input_list', 'checks_status', 'page_images'])
def test_malformed_bundle_returns_structured_invalid(application, capsys, mutation):
    root, _ = application
    assert build(capsys, root)[0] == 0
    path = root / 'outputs/example/r01/bundle.json'
    record = json.loads(path.read_text())
    if mutation == 'input_list':
        record['context']['inputs']['evidence'] = []
    elif mutation == 'checks_status':
        record['checks_status'] = 'approved'
    else:
        record['page_images'] = 'yes'
    path.write_text(json.dumps(record), encoding='utf-8')
    code, result = invoke(capsys, root, 'verify-bundle', '--bundle', 'outputs/example/r01/bundle.json')
    assert code == 2 and result['status'] == 'invalid'


def test_page_image_cli_keeps_stdout_machine_readable(application):
    pytest.importorskip('pymupdf')
    from cv_toolkit.render import _find_chromium
    if _find_chromium() is None:
        pytest.skip('Chromium is unavailable')
    root, _ = application
    result = subprocess.run([sys.executable, '-m', 'cv_toolkit.cli', 'build-application',
                             '--workspace', str(root), '--application', 'applications/example',
                             '--output', 'outputs/example/images', '--page-images'],
                            capture_output=True, text=True, timeout=240)
    assert result.returncode == 0, result.stdout
    record = json.loads(result.stdout)
    assert record['checks_status'] == 'passed'
    directory = root / 'outputs/example/images'
    checks = json.loads((directory / 'checks.json').read_text())
    images = list(directory.glob('*.png'))
    assert len(images) == sum(check['pages'] for name, check in checks.items() if name.endswith('.pdf'))
    assert all(image.read_bytes().startswith(b'\x89PNG\r\n\x1a\n') for image in images)
