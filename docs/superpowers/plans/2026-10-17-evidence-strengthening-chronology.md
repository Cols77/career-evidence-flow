# Evidence Strengthening and Chronology Implementation Plan

> **For agentic workers:** Execute these focused documentation tasks inline; use actual independent agents for behavior validation. Keep private evidence and unrelated files untouched.

**Goal:** Require a selective pre-draft evidence assessment and explicit reverse-chronology review.

**Architecture:** Extend existing skill instructions and references, using ordinary private notes and existing evidence/question records. Generate host/package copies from canonical `skills/`. No new CLI gate or schema.

**Tech Stack:** Markdown skill policy, Python skill-copy tooling, pytest and independent synthetic behavior scenarios.

## 1. Establish behavior baseline

- [x] Run an independent synthetic scenario against the unchanged skills, with urgency, sufficient general evidence, weak experiment outcomes and misordered employer streams.
- [x] Observe that a strengthening interview and chronology repair are not currently required. Preserve the actual agent result separately from deterministic tests.

## 2. Integrate focused strengthening

- [x] Update `skills/application-materials/SKILL.md` and `references/drafting-workflow.md` with the mandatory opportunity assessment, selective questions, waiting/dispositions and private review-note dependency.
- [x] Update `skills/experience-capture/SKILL.md` and `references/evidence-and-interview.md` for JD-relevant outcomes/learning, reuse, no token questions, and canonical persistence before use.
- [x] Update `docs/application-workflow.md` and `AGENTS.md` so entrypoint and stage order match.

## 3. Integrate chronology and review

- [x] Define reverse chronology in the drafting reference, including ongoing roles, overlapping/resumed intervals, tie-breaks and page continuations.
- [x] Update `skills/resume-review/SKILL.md`, `references/rubric.md` and `references/review-packet.md` to require independent checks of assessment/dispositions, experiment evidence strength and source/rendered order.
- [x] Distinguish required repairs from optional style preferences and preserve honest narrow evidence when the owner cannot supply more.

## 4. Generate and validate

- [x] Run `rtk proxy .venv/Scripts/python tools/sync_skills.py`.
- [x] Use independent behavior scenarios against the revised canonical skills: material unanswered outcome, no useful gap, explicit skip/decline, qualitative negative result, formatting-only edit and chronological inversion across page breaks.
- [x] Run `rtk proxy .venv/Scripts/python -m pytest -q` and `rtk proxy .venv/Scripts/python tools/sync_skills.py --check`.
- [x] Review the exact public diff for consistency, candidate data and accidental generated-copy edits. Report actual test results and any limitations. Do not claim runtime enforcement.

**Verification:** 580 tests passed and 7 skipped. Generated Codex/Claude/package copies match canonical skills. The existing ignored local Hermes installation was backed up, refreshed with the same generator and compared with canonical files. Two independent revised-policy exercises passed the scenario cases above; these are actual policy behavior exercises, not machine-enforcement tests. The independent consistency review's single-repo/private-workspace wording finding was repaired. The external private denylist worktree scan passed with zero findings, and `git diff --check` passed. Existing unrelated user files were left untouched. No resume regeneration, new candidate outcomes or runtime enforcement is claimed by this workflow-only change.

## Follow-up implementation: page balance, depth and hook budget

- [x] Reproduce the weak page-count-only behavior with a positioned two-page PDF test before implementing `src/cv_toolkit/page_layout.py` and its `ats.py` observation field.
- [x] Add synthetic tests for uneven nonfinal fill, sparse final pages, balanced pages, unavailable HTML/blank/rotated/custom-unit geometry and physical equivalence under scale/shifted cropboxes.
- [x] Require explicit page-balance review and full-profile inclusion/omission reasoning in canonical drafting/review guidance; sync host/package copies.
- [x] Test installed Codex/Claude timeout definitions before changing defaults to 120 seconds, preserving Codex Interrupt's three-second maximum.
- [x] Include `page_layout.py` in the release allowlist and distribution assertion after the full suite caught its initial omission.
- [x] Obtain independent bounded code/policy review; repair the pending-item deferral/waiting inconsistency and recheck it.
- [x] Complete the final full-suite rerun, copy checks and external private denylist scan; report actual outcomes separately from independent candidate review artifacts.

These follow-up changes add advisory geometry observations and agent-review obligations, not automated semantic approval or guarded release. Native trust is not granted or bypassed.

**Follow-up verification:** the first full run caught an omitted `page_layout.py` release-allowlist entry; after the explicit allowlist/distribution-test repair, the complete rerun passed **589 tests, 7 skipped**. Focused geometry/timeout/ATS/audit tests passed (29), as did the packaging/geometry/timeout recheck (11). Generated skill copies and the existing ignored Hermes installation match canonical policy. Independent bounded code review's waiting/deferral consistency finding was repaired and rechecked with no remaining medium/blocking findings. The external private denylist scan and whitespace diff check passed. Candidate review evidence and manual hook-runner probe results are retained separately in the ignored workspace; neither establishes native hook trust or submission approval.
