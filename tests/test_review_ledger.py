"""Review coverage ledger on fictional bundles: declarations, never approval."""
import json

from test_application_tools import application, build, invoke  # noqa: F401 (fixture)

BUNDLE = 'outputs/example/r01/bundle.json'


def record(capsys, root, *args):
    return invoke(capsys, root, 'record-review', '--bundle', BUNDLE, *args)


def test_pass_verdict_stores_current_artifact_hashes(application, capsys):
    root, _ = application
    assert build(capsys, root)[0] == 0
    code, status = record(capsys, root, '--document', 'resume', '--angle', 'factual', '--verdict', 'pass')
    assert code == 0 and status['angles']['resume.factual']['state'] == 'recorded'
    ledger = json.loads((root / 'outputs/example/r01/reviews.json').read_text())
    entry = ledger['reviews'][0]
    assert set(entry['artifacts']) == {'resume-ats.html', 'resume-branded.html'}
    assert status['release_available'] is False and status['review_status'] == 'unreviewed_preview'


def test_findings_verdict_needs_a_findings_file(application, capsys):
    root, _ = application
    assert build(capsys, root)[0] == 0
    code, _ = record(capsys, root, '--document', 'resume', '--angle', 'voice', '--verdict', 'findings')
    assert code == 2
    (root / 'outputs/example/voice.md').write_text('Fictional finding', encoding='utf-8')
    code, _ = record(capsys, root, '--document', 'resume', '--angle', 'voice', '--verdict', 'findings',
                     '--findings', 'outputs/example/voice.md')
    assert code == 0


def test_letter_angle_is_refused_for_the_resume(application, capsys):
    root, _ = application
    assert build(capsys, root)[0] == 0
    code, _ = record(capsys, root, '--document', 'resume', '--angle', 'persuasiveness', '--verdict', 'pass')
    assert code == 2
    assert not (root / 'outputs/example/r01/reviews.json').exists()


def test_status_lists_recorded_and_missing_angles(application, capsys):
    root, _ = application
    assert build(capsys, root)[0] == 0
    for angle in ('factual', 'alignment', 'voice', 'readability', 'visual'):
        assert record(capsys, root, '--document', 'resume', '--angle', angle, '--verdict', 'pass')[0] == 0
    code, status = invoke(capsys, root, 'review-status', '--bundle', BUNDLE)
    assert code == 0 and status['coverage'] == 'incomplete'
    assert status['missing'] == ['cover_letter.' + a for a in
                                 ('factual', 'persuasiveness', 'motivation', 'voice', 'visual')]


def test_changed_artifact_turns_its_verdict_stale(application, capsys):
    root, _ = application
    assert build(capsys, root)[0] == 0
    assert record(capsys, root, '--document', 'resume', '--angle', 'visual', '--verdict', 'pass')[0] == 0
    (root / 'outputs/example/r01/resume-ats.html').write_text('<p>rebuilt</p>', encoding='utf-8')
    status = invoke(capsys, root, 'review-status', '--bundle', BUNDLE)[1]
    assert status['angles']['resume.visual']['state'] == 'stale'


def test_resume_only_policy_requires_no_letter_angle(application, capsys):
    root, app = application
    record_path = app / 'application.json'
    data = json.loads(record_path.read_text())
    data['policy']['deliverables'] = ['resume']
    for key in ('cover_letter_source', 'cover_letter_claims'):
        data.pop(key, None)
    record_path.write_text(json.dumps(data), encoding='utf-8')
    assert build(capsys, root)[0] == 0
    status = invoke(capsys, root, 'review-status', '--bundle', BUNDLE)[1]
    assert set(status['angles']) == {'resume.factual', 'resume.alignment', 'resume.voice', 'resume.readability',
                                     'resume.visual'}
