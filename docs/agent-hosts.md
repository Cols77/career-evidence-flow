# Load the agent workflows

`skills/` is the single authored source. `tools/sync_skills.py` generates complete copies into the package and the repository's native host directories. Supporting references travel with each skill; no installed skill depends on this checkout being present. See [the application workflow](application-workflow.md).

For a fresh or existing private workspace, use `cv setup ROOT --host codex`,
`--host claude`, `--host hermes` or `--host all`, then
`cv doctor --workspace ROOT --host HOST`. See [portable deployment](deployment.md)
for package installation, repeatable setup and distribution builds. The commands
install/check local files; they do not verify native discovery or review execution.

For one cloned repository, use `cv setup user-profile --host all --project-root .`
and the same roots with `doctor` and `install-hooks`. Start the host at the
repository root; data lives in ignored `user-profile/`. Skills and hooks live at
the project root. Read the generated local `RESUME_TOOLKIT.md` for the pinned
interpreter and exact data path. Omitting `--project-root` retains the external
workspace layout, where host files and data share one root. Never select a
workspace based on the first employer folder or a global `cv` executable.

## Codex

Launch Codex from this checkout. Its project copies are in `.agents/skills/`; explicitly request `$application-materials` or ask it to use that skill. `AGENTS.md` also provides a manual entrypoint. Codex documents repository discovery in `.agents/skills` from the current directory to the repository root. See [official OpenAI documentation](https://learn.chatgpt.com/docs/build-skills).

For a separate private workspace, run `cv install-skills --workspace ROOT --host codex`, start the host there and confirm the five skill names are visible. If its discovery rules require a repository root, keep that workspace in a private local Git repository. Existing skill folders are not replaced.

`cv install-hooks --workspace ROOT --host codex` installs native local lifecycle definitions and a standalone adapter. It reuses the canonical onboarding classifier and restores explicit session checkpoints across resume/compaction. It never changes feature settings or grants hook trust. See [Codex workflows](codex-workflows.md) for activation, isolation, checkpoint/freshness commands, delivery probes and tested versus unverified surfaces. Selected-byte freshness does not authenticate reviews or guard release.

## Claude Code

Launch Claude Code from this checkout. Generated project skills are in `.claude/skills/`; use `/application-materials`. `CLAUDE.md` points to the shared agent instructions. Claude documents this directory as project scope and exposes the skill name as a slash command. See [Claude Code skills](https://code.claude.com/docs/en/skills).

For a separate workspace, use `cv install-skills --workspace ROOT --host claude` and confirm the command is available in a session there. Reload or restart if the host does not pick up a newly created top-level skills directory.

Optional entry hooks install with `cv install-hooks --workspace user-profile --project-root . --host claude`.
They merge `SessionStart` and `UserPromptSubmit` command groups into
`.claude/settings.local.json`, preserve unrelated settings and hooks, and refuse
conflicting toolkit installations. The bundled runner and validators live in
`.claude/hooks/resume-toolkit/`. Inspect those files and restart Claude Code in
the project. The adapter uses command hooks with an executable and an `args`
array; the installed host must support that form. See
[Claude hooks](https://code.claude.com/docs/en/hooks).

Both events classify the bound data workspace and return advisory workflow
context. They require a session ID and a cwd within the project, reject other
nested workspaces, and never derive a data path from prompt text. They do not
persist answers, restore Codex checkpoints, authenticate independent review, or
approve documents. Installed-runner tests establish routing, not native event
delivery; verify delivery in a fresh host session before claiming it.

## Hermes

Current Hermes documents project discovery of `.hermes/skills/` and `.agents/skills/` at a Git project root, after explicit project trust. This checkout uses the generated `.agents/skills/` copies. Inspect the skills before running `hermes skills trust` from the checkout; that command changes your Hermes trust configuration, and the toolkit does not run it automatically. Then confirm the skills are listed and invoke `/application-materials`. See [Hermes skills system](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills/).

`cv install-skills --workspace ROOT --host hermes` writes workspace-local `.hermes/skills/` copies. They are not your global `~/.hermes/skills/` installation. A standalone directory without a Git root or project trust may not be discovered. Older hosts may require their documented external-directory configuration; the toolkit does not alter it.

For a guided fresh setup (venv, private workspace, state routing, skills and entry-hook opt-in), see [getting-started.md](getting-started.md).

### Hermes entry-hook routing (workspace `cv onboard` route)

`cv install-hooks --workspace ROOT --host hermes` installs a packaged `pre_llm_call` entry plugin at `ROOT/.hermes/plugins/resume-toolkit/` (plugin.yaml, `__init__.py`, `onboarding.py`, plus bundled `cv_toolkit` validators). It writes files only; it never changes live Hermes config or global memory. The plugin activates only after explicit, separate opt-ins:

1. **Project plugin discovery**: Hermes scans `.hermes/plugins/` only when project plugins are enabled — set `HERMES_ENABLE_PROJECT_PLUGINS=1` (docs use `true`) before launching Hermes.
2. **Enable/trust**: run `hermes plugins enable resume-toolkit` (or the equivalent enable/trust command for the installed version) and review the plugin at `ROOT/.hermes/plugins/resume-toolkit/` first; the toolkit runs no trust command itself.

With `--project-root PROJECT`, the plugin is installed under that project's
`.hermes/plugins/` and its binding identifies the child data workspace. Restart
Hermes from the exact project root after installing skills or enabling the plugin.

The hook is scoped and advisory:
- It supports only a **dedicated CLI process launched at the exact project root**, with an explicit `platform='cli'` hook payload; it stays **silent** for missing/unknown platforms or when process cwd differs from the plugin's project root. **Hermes desktop and gateway processes are not certified.**
- It returns `pre_llm_call` user context each turn, routing the agent to the workflow determined by the read-only `cv onboard --workspace ROOT` classifier (`experience-capture` for capture/interview/import, `application-materials` when ready, etc.).
- It is **advisory routing, not a sandbox**: structural validity does not prove factual truth, and approval/release is never asserted. It validates local records including claim text, but does not follow original source documents or include candidate claim text in routing context.

Verify in a fresh, dedicated CLI session at `ROOT` that the plugin and the five skills are listed, then run a synthetic job-to-preview scenario. Do not claim production acceptance from fixture records.

## Other hosts and manual loading

### Desktop: explicit workspace routing, not a process-cwd hook

In a shared desktop process, do not enable this project hook as a substitute for
session workspace identity. The documented `pre_llm_call` payload and the inspected
Hermes implementation supply session/platform identifiers, but no workspace path.
Do not infer it from message text, global cwd, another session or global memory.

Instead, use the user's explicit private workspace for each operation:

1. Run the installed `cv onboard --workspace ABSOLUTE_ROOT` command.
2. Follow its returned state. For `unconfigured` or `malformed`, repair/setup
   before drafting; otherwise load the returned workflow from
   `PROJECT_ROOT/.hermes/skills/SKILL_NAME/SKILL.md` and its references, using the
   project root from the local startup guide (same as `ABSOLUTE_ROOT` when no
   separate project root was configured).
3. If native project discovery is unavailable, use absolute-path file reads.
   File reads are a fallback, not proof of `skills_list`/`skill_view` discovery.
4. Pass that same explicit root to subsequent `cv` commands. After a workspace
   switch, re-run onboarding for the new root; never reuse the previous route.

This is host-directed use of existing commands, not automatic desktop hook
support. Automated desktop routing remains blocked on a documented session-scoped
workspace contract and real multi-session isolation tests. No desktop UI plugin
or new core tool is required for this explicit workflow.

The reference contract is the [Hermes pre-LLM hook documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/hooks#pre_llm_call).
Check the installed host's payload before expanding this adapter's scope; do not
assume a future extra field is trustworthy without verifying its session binding.

Give the host `AGENTS.md` and the full path to `skills/application-materials/SKILL.md`, or to its installed copy. Ask it to read the linked references. Explicitly state the private workspace and installed `cv` executable. File access, conversations, delegation, browsing and artifact inspection are supplied by the host. If one is unavailable, report the missing capability and continue only the supported preview stages.

## Acceptance evidence

New Codex and Claude command-hook installations use a 600-second (10-minute) timeout to allow slow local Python startup and workspace checks on heavily loaded machines. This is a per-handler ceiling, not a mandatory wait. Hermes uses an in-process plugin without a toolkit-configured timeout. Codex Interrupt handlers retain their documented three-second maximum. The installer does not overwrite an existing installation; when updating one, preserve unrelated handlers/settings, back up its configuration and change only toolkit definitions. These settings are seconds, not milliseconds. A successful manual runner probe verifies the runner, not host delivery or trust. [Codex hook documentation](https://learn.chatgpt.com/docs/hooks) requires review/trust of changed non-managed definitions through `/hooks`; the toolkit does not bypass that trust decision.

Automated tests check distribution consistency, reference resolution and installation without overwrites. A wheel installation should also be exercised outside the checkout. A manual agent scenario can prove that the instructions guide actual tool use, but does not prove native discovery in another host.

`tests/test_entry_hook.py` exercises real Hermes lifecycle dispatch without
inference. Its platform checks reject ambiguous context before reading records.
`tests/test_onboard_cli.py` checks explicit-root routing across workspace switches
without relying on the process cwd or mutating candidate records.
`tests/test_hermes_skill_discovery.py` exercises native `skills_list` and
`skill_view` against temporary trusted/untrusted project roots, checks the exact
installed source path and a linked reference, and verifies no-Git non-discovery.
These tests use an isolated `HERMES_HOME` and no inference calls; they skip when
no Hermes interpreter is available. They prove API discovery, not a desktop
menu or a complete live-agent drafting/review run.

To verify native discovery, start a fresh session in the chosen scope, confirm the five skills in its index/menu, load application-materials and one linked reference, and run a synthetic job-to-preview scenario. Preserve actual host/version, scope and tool outcomes in private local verification notes. Do not use fixture review records to claim production acceptance. No global host configuration, trust or paid provider calls are changed by the installer.
