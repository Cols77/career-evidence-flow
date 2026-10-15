# Portable host setup and review audit

**Goal:** Install and diagnose the existing agent-led toolkit in a private workspace from a distributable wheel, for Codex, Claude Code and Hermes, without depending on this checkout.

**Design:** Keep one Python distribution and the four canonical skills. Native project skill directories already provide the shared integration; a new `cv setup DIRECTORY --host HOST` composes initialization and complete skill installation. `all` installs all three. A read-only `cv doctor --workspace DIRECTORY --host HOST` distinguishes installed files, prerequisites and unverified host execution. Hook installation and host trust remain explicit existing commands. A standard wheel and source distribution, checksums and installation instructions provide deployment artifacts; no new hosted service, credential storage or model calls.

**Alternatives considered:** Host-specific plugins would add three release formats while still requiring Python and private workspace configuration. A container would complicate desktop file access and browser rendering. The existing Python package plus native skills is the smallest portable route.

**Scope:** Do not migrate private candidate workspaces or modify global host configuration. Keep all real audit findings, candidate wording and generated CVs outside the public repository. No claim of native runtime acceptance from file installation or automated fixtures.

## Implementation and validation

- [x] Independently audit real review notes, artifact hashes and available lifecycle evidence. Record verified execution separately from missing evidence and semantic quality defects.
- [x] Add failing behavioral tests for setup on a new workspace, repeated setup, existing profile preservation, conflicts before partial writes, selected/all hosts, and read-only diagnostics.
- [x] Implement setup/doctor in a focused module and CLI routes. Reuse packaged resources and existing validators. Preserve customized instructions and reject conflicting skill files; do not grant trust or enable hooks. Document exact recovery for conflicts.
- [x] Strengthen the existing editorial criteria: skills must express meaningful capabilities or relevant tools, rather than merely naming routine workflow artifacts. Independent reviewers must explicitly assess selection as well as factual support.
- [x] Correct the active private CV, retain factual detail in experience where useful, rerender a new revision and obtain actual independent factual/voice/visual review of all pages.
- [x] Update install documentation for Windows and POSIX, neutral private workspace names, synthetic examples, optional hooks and explicit first prompts. Include current official host documentation.
- [x] Add a repeatable release builder producing wheel/sdist and SHA-256 checksums; verify the built distribution in an isolated environment outside the checkout. Exercise setup/doctor for each host, repeated setup and the packaged fictional rendering matrix.
- [x] Run `python -m pytest -q`, `python tools/sync_skills.py --check`, independent code review and the external private denylist scan before publishing changes. Report actual tested surfaces and remaining runtime limitations.

**Acceptance:** Colleagues can install the wheel with pip, run one setup command, diagnose their workspace and load a complete skill including references with any of the three hosts. Existing private evidence is preserved. No paid inference or trust changes occur during installation. Reviews remain attributable working notes and previews remain previews.

**Verification completed:** 531 tests passed, 6 skipped; generated skills match canonical sources. Version 0.2.0 was built and installed in an isolated Windows environment outside the checkout. Installed acceptance passed selected/all-host setup, repeat setup, preserved profile/instruction bytes and timestamps, read-only diagnostics, 10 synthetic resume/letter PDFs and the four-style, two-page gallery. All 26 distribution checksums match, the wheel matches current package source, and 159 unpacked artifact/document files passed the external private-content scan. Independent code review closed malformed-empty-profile projection and standalone documentation-link findings. The release includes 23 allowlisted Markdown documents with working offline links. Actual live host discovery and end-to-end agent sessions remain separate, unverified acceptance surfaces.
