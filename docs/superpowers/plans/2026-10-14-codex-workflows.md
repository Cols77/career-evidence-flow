# Codex workflow support implementation plan

> **For agentic workers:** Use executing-plans to implement this plan task-by-task. The user authorized the isolated implementation; independent review follows in the parent workflow. Do not commit or activate live hooks during implementation.

**Goal:** Install native Codex lifecycle routing and restore explicitly recorded work across interruption/compaction for all four toolkit skills.

**Architecture:** A standalone bundled Python adapter validates the hook's explicit session/cwd against the installation's absolute workspace and reuses the canonical classifier. Private, atomic, session-scoped checkpoints contain bounded workflow metadata and optional file fingerprints. Fingerprints establish only byte freshness; hooks and checkpoint records cannot establish independent review, visual inspection, approval or release.

**Tech Stack:** Python 3.11+, standard-library JSON/hashlib/pathlib, pytest, Codex command hooks.

## Task 1: Session adapter and explicit checkpoints

Files: create `src/cv_toolkit/codex_hooks.py`, `tests/test_codex_hooks.py`.

- [x] Write synthetic tests calling `dispatch(payload, workspace)` and `record_checkpoint(workspace, session_id, skill, phase, paths)`; reject invalid event types, relative/wrong cwd, missing session, malformed state, path traversal and escaping symlinks.
- [x] Run `python -m pytest tests/test_codex_hooks.py -q` and observe missing API failures.
- [x] Implement canonical `classify(workspace)` routing for SessionStart/UserPromptSubmit; persist only enum metadata, session/workspace digests and caller-selected file path/hash pairs. Never store prompt, transcript, candidate identifiers or message text. Use exclusive per-session lock and atomic replace to avoid partial/lost writes.
- [x] Implement PreCompact/Interrupt/Stop observation without blocking or continuation. Restore via SessionStart (including compact/resume); reclassify before returning context. Treat interrupted/paused/waiting checkpoints as context, never automatic authorization to resume.
- [x] Implement `checkpoint_status(workspace, session_id)` comparing recorded hashes to actual confined files. Return `not_recorded`, `fresh`, or `stale`; never approved or submission-ready.
- [x] Run the focused tests and confirm all pass.

## Task 2: Portable installation and CLI

Files: modify `src/cv_toolkit/bootstrap.py`, `src/cv_toolkit/cli.py`, `tests/test_entry_hook.py`; extend `tests/test_codex_hooks.py`.

- [x] Add failing install tests for `.codex/hooks.json`, complete verbatim bundled validators, Python isolated execution outside the checkout, no overwrite, user-owned config preservation, unsupported Claude host and path quoting.
- [x] Generate explicit absolute commands with POSIX shell quoting and Windows PowerShell single-quoted arguments/call operator. Bundle a runner plus canonical Python modules; runner passes its installed workspace to `main` and does not use package imports from the checkout.
- [x] Install only to the requested workspace; refuse existing config/adapter before writing, including symlink escapes. Keep Hermes payload unchanged. Do not alter host feature/trust settings.
- [x] Add CLI commands: `cv workflow-checkpoint --workspace ROOT --session-id ID --skill resume-review --phase working --file outputs/resume.pdf` and `cv workflow-status --workspace ROOT --session-id ID`. Expose preview-only status and no runtime-discovery assertion.
- [x] Test direct CLI calls and invoke the installed command using synthetic JSON stdin from a directory with spaces.

## Task 3: Workflow policy and setup documentation

Files: modify the four `skills/*/SKILL.md` files and `docs/agent-hosts.md`; create `docs/codex-workflows.md`; generate skill copies with `tools/sync_skills.py`.

- [x] Tell each workflow how to record bounded checkpoints, preserve questions/answers in existing canonical records, and resume only authorized work.
- [x] Tell authors to dispatch actual independent reviewers with exact files, preserve actual tool/run references in private notes, inspect every requested rendered page and rerun affected checks after edits. Checkpoint freshness never authenticates those observations.
- [x] Document installation, `/hooks` trust, host feature check, root/session binding, failure recovery, `workflow-status` diagnostic, no forced Stop continuation and exact tested/unverified surfaces. Cite official hook semantics, including SessionStart compact restoration and unsupported cloud orchestration.
- [x] Run `python tools/sync_skills.py` then `python tools/sync_skills.py --check`.

## Task 4: Verification and parent handoff

- [x] Run `python -m pytest -q`; fix regressions including Hermes behavior.
- [x] Build a fresh wheel without downloading dependencies; install outside the checkout and exercise Codex installation/dispatcher with synthetic files, stripped PYTHONPATH and Python isolated mode.
- [x] Review diff for private data, misleading completion claims and accidental generated-policy edits. Parent performs separate review/acceptance and any publication scan.
- [x] Report actual test counts, changed APIs, activation steps, limitations and any manual acceptance still required. No commit/push/merge or live configuration mutations.

## Verification evidence

- Full suite: 460 passed, 6 skipped in 72.06s; three new skips require Windows symlink privileges, while NTFS junction regressions ran and passed.
- Generated skill consistency: python tools/sync_skills.py --check passed.
- Parent independently built/installed a fresh wheel outside the checkout and verified all four skills, generated PowerShell commands, standalone bundle isolation, session scoping, compact restoration, interruption, no overwrite and fresh-to-stale snapshots.
- Independent reviewer reported no outstanding material findings after fixes; installer alias and root-directory alias regressions failed before fixes and pass now.
- Native trusted hook delivery and a live end-to-end application/reviewer/visual session remain unverified; activation/probe steps are documented. No commit, merge, push or global host/trust mutations performed.
