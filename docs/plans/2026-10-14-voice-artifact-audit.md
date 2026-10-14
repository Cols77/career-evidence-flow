# Voice and artifact audit implementation plan

> Execute the approved design in the existing drafting, independent review and document-check workflow. Do not add a fifth skill, new hook, detector service or duplicate reviewer.

**Goal:** Preserve the candidate's voice and factual scope while making the final PDF's observable metadata and hidden-content indicators reviewable.

**Architecture:** One shared reference under application-materials owns the voice-profile convention and editorial procedure. Existing review skills link to it. The shared resume/letter document checker adds a sanitized, read-only artifact audit using the existing pypdf dependency. Findings are observations, not AI-authorship scores or release approval.

**Approved scope:** Optional private writing preferences and authentic samples; one editorial pass followed by factual recheck; metadata, attachment, watermark annotation and text-rendering indicator inspection; existing visual inspection and exact-byte review remain necessary. Preserve employer AI-use rules. Never invent reactions or introduce mistakes to influence detectors.

## Tasks

- [x] Baseline: run existing tests and a separate-agent scenario against current skills; record missing voice-profile and artifact-audit mechanisms.
- [x] Extend the existing `cv check` result with `artifact_audit`. Write failing synthetic-PDF tests for sanitized metadata, attachments, watermark annotations, invisible text-rendering operators, format characters, unsupported/unreadable input and shared resume/letter behavior. Preserve input bytes and existing check status semantics.
- [x] Implement the smallest shared audit with explicit observation limits; use existing extraction, parser and dependency rather than another rendering/check command.
- [x] Add one shared voice reference; replace overlapping drafting/rubric prose with links. Specify a private `writing-voice.md` in the configured profile directory, preferences with provenance, optional authentic samples, default versus confirmed preferences, and inclusion in existing review packets/checkpoint snapshots.
- [x] Generate native and packaged skill copies with `python tools/sync_skills.py`; run skill scenario again with the updated references.
- [x] Independently review implementation and policy; repair concrete defects. Run `python -m pytest -q`, `python tools/sync_skills.py --check`, and external private-denylist scan before committing public files.
- [x] Update existing installed private skill copies after backing up and comparing them to the previous packaged revision; audit actual resume PDFs locally, preserving their bytes. Integration continues with the authorized merge, push and next application.

## Validation and boundaries

Tests must establish what each reported indicator actually measures. PDF graphics, images, clipping and all possible text visibility cannot be certified by these checks; inspect rendered pages independently. Metadata values, attachment names and extracted candidate text must not appear in diagnostic output. Report ordinary renderer metadata without treating it as AI authorship. Preserve genuine signatures/provenance and formatting rather than automatically stripping them. No network uploads or third-party skill installation.

The native worktree tool failed on existing repository ownership. Implementation uses a dedicated local branch and command-scoped Git ownership configuration, preserving the pre-existing untracked file.

## Verification results

The baseline agent confirmed missing voice-profile discovery and PDF observations. The updated scenario preserved experimental maturity and approximate quantities and reused the existing reviewer. Independent code review found duplicate attachment names were undercounted; a failing regression reproduced this and passed after using the library attachment iterator. The existing pypdf minimum is now 5.9 to support that API without a duplicate parser. Final runtime suite: 482 passed, 6 skipped. PDF checks/render tests also passed on pypdf 5.9.0 (48 tests). Skill-distribution checks passed after the final reference deduplication. Actual private exported PDFs passed the new read-only audit with byte hashes unchanged.
