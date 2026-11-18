"""Owner edits of a release's Markdown and the shared reviewer briefs, on fictional bundles."""
from test_application_tools import application, build, invoke  # noqa: F401 (fixture)

R01 = 'outputs/example/r01'


def regenerate(capsys, root, *args):
    return invoke(capsys, root, 'regenerate', '--from', R01, *args)


def test_build_writes_editable_copies_equal_to_the_frozen_sources(application, capsys):
    root, app = application
    assert build(capsys, root)[0] == 0
    output = root / R01
    for name, source in (('resume.md', 'resume.md'), ('cover-letter.md', 'cover-letter.md')):
        frozen = output / 'inputs/applications/example' / source
        assert (output / name).read_bytes() == frozen.read_bytes() == (app / source).read_bytes()


def test_editing_a_copy_keeps_the_bundle_and_its_reviews_valid(application, capsys):
    root, _ = application
    assert build(capsys, root)[0] == 0
    code, before = invoke(capsys, root, 'record-review', '--bundle', R01 + '/bundle.json',
                          '--document', 'resume', '--angle', 'factual', '--verdict', 'pass')
    assert code == 0
    copy = root / R01 / 'resume.md'
    copy.write_text(copy.read_text(encoding='utf-8') + '\nOwner edit.\n', encoding='utf-8')
    assert invoke(capsys, root, 'verify-bundle', '--bundle', R01 + '/bundle.json')[1]['freshness'] == 'fresh'
    code, after = invoke(capsys, root, 'review-status', '--bundle', R01 + '/bundle.json')
    assert code == 0 and after['angles'] == before['angles']


def test_diff_reports_the_edits_and_builds_nothing(application, capsys):
    root, app = application
    assert build(capsys, root)[0] == 0
    copy = root / R01 / 'resume.md'
    copy.write_text(copy.read_text(encoding='utf-8') + '\nShorten the summary please.\n', encoding='utf-8')
    source = (app / 'resume.md').read_bytes()
    code, result = regenerate(capsys, root, '--diff')
    assert code == 0 and list(result['changes']) == ['resume.md']
    assert '+Shorten the summary please.' in result['changes']['resume.md']
    assert sorted(p.name for p in (root / 'outputs/example').iterdir()) == ['r01']
    assert (app / 'resume.md').read_bytes() == source


def test_regenerate_builds_the_next_revision_from_the_edits(application, capsys):
    root, app = application
    assert build(capsys, root)[0] == 0
    copy = root / R01 / 'resume.md'
    edited = copy.read_text(encoding='utf-8').replace('\n', '\n\nOwner rewrite.\n', 1)
    copy.write_text(edited, encoding='utf-8')
    code, result = regenerate(capsys, root)
    assert code == 0 and result['bundle'] == 'outputs/example/r02/bundle.json'
    assert 'cv review-plan' in result['next'] and 'r02/bundle.json' in result['next']
    r02 = root / 'outputs/example/r02'
    assert (app / 'resume.md').read_text(encoding='utf-8') == edited
    assert (r02 / 'resume.md').read_text(encoding='utf-8') == edited
    assert 'Owner rewrite.' in (r02 / 'resume-branded.html').read_text(encoding='utf-8')
    assert (r02 / 'checks.json').is_file() and not (r02 / 'resume-ats.pdf').exists()  # same html format
    assert {'resume-ats.html', 'resume-branded.html', 'cover-letter.html'} <= set(result['documents'])


def test_regenerate_takes_the_next_free_revision(application, capsys):
    root, _ = application
    assert build(capsys, root)[0] == 0
    assert regenerate(capsys, root)[1]['bundle'] == 'outputs/example/r02/bundle.json'
    assert regenerate(capsys, root)[1]['bundle'] == 'outputs/example/r03/bundle.json'


def test_regenerate_overwrites_a_source_changed_after_the_revision(application, capsys):
    root, app = application
    assert build(capsys, root)[0] == 0
    (app / 'resume.md').write_text('# Newer agent draft\n', encoding='utf-8')
    release = (root / R01 / 'resume.md').read_bytes()
    code, _ = regenerate(capsys, root)
    assert code == 0
    assert (app / 'resume.md').read_bytes() == release
    assert (root / 'outputs/example/r02/resume.md').read_bytes() == release


def test_review_plan_lists_only_angles_without_a_current_verdict(application, capsys):
    root, _ = application
    assert build(capsys, root)[0] == 0
    from cv_toolkit.application_tools import ANGLES
    for angle in ANGLES['resume']:
        assert invoke(capsys, root, 'record-review', '--bundle', R01 + '/bundle.json', '--document', 'resume',
                      '--angle', angle, '--verdict', 'pass')[0] == 0
    code, plan = invoke(capsys, root, 'review-plan', '--bundle', R01 + '/bundle.json')
    assert code == 0 and plan['todo'] == ['cover_letter.' + a for a in ANGLES['cover_letter']]
    assert set(plan['briefs']) == set(plan['todo'])
    assert 'record-review' in plan['briefs']['cover_letter.voice']


def test_readability_brief_keeps_the_reviewer_cold(application, capsys):
    root, _ = application
    assert build(capsys, root)[0] == 0
    code, plan = invoke(capsys, root, 'review-plan', '--bundle', R01 + '/bundle.json',
                        '--angle', 'resume.readability', '--command', 'python -m cv_toolkit.cli')
    brief = plan['briefs']['resume.readability']
    assert code == 0 and list(plan['briefs']) == ['resume.readability']
    assert 'ONLY the rendered resume artifact and the frozen job text' in brief
    assert 'never open evidence' in brief and 'python -m cv_toolkit.cli record-review' in brief
