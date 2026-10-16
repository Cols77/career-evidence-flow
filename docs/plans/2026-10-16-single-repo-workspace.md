# Single-repository workspace implementation plan

**Goal:** A clone supplies every toolkit component; an ignored `user-profile/` holds a real user's standard workspace, and each supported host routes to that explicit workspace from the repository root.

**Architecture:** Keep the existing evidence, registry, projection and application schemas. Separate the host project root from the candidate workspace through an explicit optional `--project-root`; the data workspace must be contained by that project. Default same-root behavior remains compatible. Python provides records, rendering and advisory hooks; the host still performs interviews, drafting and independent reviews. Hooks do not certify completion or submit applications.

**User direction:** Consolidate into one clean repository, preserve local personal data in an ignored directory, audit all three hosts, and remove obsolete worktrees/branches without losing work.

## 1. Independent audit

- [x] Assign independent core-workflow, host-hook and personal-data reviews.
- [x] Validate the real workspace with the same schemas and commands used by new users.
- [x] Exercise a synthetic capture/correction/application/resume/letter workflow without a legacy repository.
- [x] Preserve reports distinguishing implemented behavior, executed checks and native runtime limitations.

## 2. Standard installation and project binding

Files: `src/cv_toolkit/cli.py`, `deployment.py`, skill-installation functions in `bootstrap.py`, focused tests.

- [x] Write failing tests for explicit child-workspace setup/doctor/skill installation, preservation of existing files, and rejection of external/aliased targets.
- [x] Add optional `--project-root` to setup, doctor, install-skills and install-hooks. Example: `cv setup user-profile --host all --project-root .`.
- [x] Keep data validation rooted at the candidate workspace and skill discovery rooted at the host project.
- [x] Generate accurate invocation instructions using the installed environment; report installed package location and unverified native discovery honestly.
- [x] Run focused tests, including existing same-root setup behavior.

## 3. Host adapters

Files: hook-installation functions in `bootstrap.py`, `codex_hooks.py`, new Claude adapter, packaged Hermes entry adapter, focused tests.

- [x] Write failing routing tests for the pinned project/workspace pair and unrelated/nested workspace rejection.
- [x] Preserve Codex checkpoint semantics while binding data access to the explicitly installed workspace.
- [x] Add Claude's documented advisory entry events with a self-contained bundle and safe local settings handling.
- [x] Bind Hermes project discovery to the project root and data classification to the intended workspace; retain dedicated CLI/platform limits.
- [x] Never grant host trust, change global configuration, infer an actual session, or label a manual probe native execution.
- [x] Exercise adapter processes/native hook APIs where available and record exact remaining runtime limits.

## 4. Local layout and privacy

Files: `.gitignore`, `AGENTS.md`, `README.md`, deployment/host/privacy docs, `tools/check_shareable.py`, privacy tests. Real files remain ignored.

- [x] Ignore `/user-profile/` and local host runtime files before moving real data.
- [x] Add a synthetic regression test proving forced staging of `user-profile/` is rejected by publication scanning.
- [x] Install the current toolkit in the checkout's `.venv`; verify its import/executable origin without the legacy renderer.
- [x] Relocate the private standard workspace without changing original evidence bytes; bring the current master and necessary original references inside it.
- [x] Archive historical helper scripts, stale host bundles and redundant artifacts outside the active workspace structure; preserve a migration manifest and hashes.
- [x] Install current skills/hooks through standard package commands; validate data, all applications and explicit routing.

## 5. Worktree and branch cleanup

- [x] Inventory every worktree, dirty/untracked file, ignored artifact category and branch ancestry against fetched main.
- [x] Preserve dirty/untracked material and its base commit in a local recovery archive; do not discard unique work.
- [x] Remove only obsolete worktrees after verifying the exact absolute paths and archive contents. Retain any active/unresolved work.
- [x] Remove merged obsolete local branches and the obsolete merged remote branch after validating ancestry; preserve main.
- [x] Verify the final worktree and branch inventory.

## 6. Final verification

- [x] Run `python -m pytest -q` and `python tools/sync_skills.py --check` in the intended installation.
- [x] Build/install the distribution in isolation and exercise both document workflows and all host installation bundles without another candidate repository.
- [x] Obtain independent review of changed routing/adapters and the migrated personal-data setup.
- [x] Scan the exact proposed public files with the external private denylist and verify zero candidate files are tracked or packaged.
- [x] Report what actually ran, what remains manual/native-unverified, and where the preserved recovery material lives.
