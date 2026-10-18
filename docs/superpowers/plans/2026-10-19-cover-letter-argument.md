# Cover-letter Argument Implementation Plan

> Execute the approved focused changes in this session. Use actual independent
> agents for behavioral validation and policy review; preserve unrelated files.

**Goal:** Make letters selective and persuasive while retaining factual scope,
genuine motivation and independent artifact review.

**Architecture:** Extend the existing application-materials drafting reference
and cover-letter-review packet/rubric. Host agents exercise judgment; existing
Python commands validate, persist and render. No new runtime gate or record schema.

**Tech Stack:** Markdown policy, existing Python skill distribution tools,
pytest and independent synthetic exercises.

## 1. Establish baseline

- [x] Run an independent fictional generic-but-supported letter through the
  unchanged review skill and record its actual findings and omissions.
- [x] Check motivation-unknown, explicitly-declined and already-strong cases.
  Distinguish observed failures from existing criteria that already work.

## 2. Integrate drafting and review

- [x] Update `skills/application-materials/SKILL.md` and
  `references/drafting-workflow.md`: brief argument, focused motivation
  assessment/disposition, selective examples and paragraph purpose.
- [x] Update `skills/cover-letter-review/SKILL.md`, `references/rubric.md`
  and `references/review-packet.md`: independent first reading, separate
  persuasiveness verdict and actionable editorial assessment.
- [x] Update `docs/application-workflow.md` and README feature/skill descriptions.
- [x] Run `rtk proxy .venv/Scripts/python tools/sync_skills.py`.

## 3. Verify behavior and distribution

- [x] Exercise revised instructions independently with fictional weak/strong
  letters and unknown/declined/already-recorded motivation. Do not claim that
  prose assertions or exact-wording tests establish semantic enforcement.
- [x] Obtain independent review of scope, consistency, references and generated
  copies; repair concrete findings.
- [x] Run `rtk proxy .venv/Scripts/python -m pytest -q` and
  `rtk proxy .venv/Scripts/python tools/sync_skills.py --check`.
- [x] Run the existing external-denylist public-file scan and `git diff --check`
  before committing/publishing any public changes.

## 4. Apply to the authorized private application revisions

- [x] Reuse confirmed evidence and actual answers; capture new motivation only
  if supplied. Keep a material interview question pending until answered/skipped.
- [x] Revise the requested letters around their role-specific arguments,
  preserving the final resumes and necessary factual boundaries.
- [x] Build fresh revision bundles with actual dependencies, obtain independent
  factual and persuasive verdicts and inspect every rendered letter page.
- [x] Verify exact exported bytes and workflow freshness; open revised letters
  and resumes explicitly in the browser and report remaining limitations.

## Verification outcome

The existing policy already identified generic letters in the independent baseline; the changes make the positive hiring argument, initial reading sequence and separate persuasiveness verdict explicit. An independent synthetic exercise identified a substantive selection defect in a supported generic letter, retained an already-strong letter, and respected unknown, declined and recorded motivation. This is behavioral evidence, not automatic enforcement. Independent policy review found no remaining issues.

The full suite passed with 655 tests passed and 9 skipped. Generated skill copies passed the synchronization check; the local Hermes installation was refreshed through the same generator. All 24 proposed public files passed the external-denylist scan. Authorized private revisions received actual independent letter reviews and all-page visual inspection; factual/publication and stale-mapping findings were repaired. Exported PDF hashes match the reviewed bytes and the requested browser handoff was performed. Candidate sources, reports and artifacts remain in the ignored workspace.
