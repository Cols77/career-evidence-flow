# Load the agent workflows

`skills/` is the single authored source. `tools/sync_skills.py` generates complete copies into the package and the repository's native host directories. Supporting references travel with each skill; no installed skill depends on this checkout being present. See [the application workflow](application-workflow.md).

## Codex

Launch Codex from this checkout. Its project copies are in `.agents/skills/`; explicitly request `$application-materials` or ask it to use that skill. `AGENTS.md` also provides a manual entrypoint. Codex documents repository discovery in `.agents/skills` from the current directory to the repository root. See [official OpenAI documentation](https://learn.chatgpt.com/docs/build-skills).

For a separate private workspace, run `cv install-skills --workspace ROOT --host codex`, start the host there and confirm the four skill names are visible. If its discovery rules require a repository root, keep that workspace in a private local Git repository. Existing skill folders are not replaced.

## Claude Code

Launch Claude Code from this checkout. Generated project skills are in `.claude/skills/`; use `/application-materials`. `CLAUDE.md` points to the shared agent instructions. Claude documents this directory as project scope and exposes the skill name as a slash command. See [Claude Code skills](https://code.claude.com/docs/en/skills).

For a separate workspace, use `cv install-skills --workspace ROOT --host claude` and confirm the command is available in a session there. Reload or restart if the host does not pick up a newly created top-level skills directory.

## Hermes

Current Hermes documents project discovery of `.hermes/skills/` and `.agents/skills/` at a Git project root, after explicit project trust. This checkout uses the generated `.agents/skills/` copies. Inspect the skills before running `hermes skills trust` from the checkout; that command changes your Hermes trust configuration, and the toolkit does not run it automatically. Then confirm the skills are listed and invoke `/application-materials`. See [Hermes skills system](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills/).

`cv install-skills --workspace ROOT --host hermes` writes workspace-local `.hermes/skills/` copies. They are not your global `~/.hermes/skills/` installation. A standalone directory without a Git root or project trust may not be discovered. Older hosts may require their documented external-directory configuration; the toolkit does not alter it.

For a guided fresh setup (venv, private workspace, state routing, skills and entry-hook opt-in), see [getting-started.md](getting-started.md).

### Hermes entry-hook routing (workspace `cv onboard` route)

`cv install-hooks --workspace ROOT --host hermes` installs a packaged `pre_llm_call` entry plugin at `ROOT/.hermes/plugins/resume-toolkit/` (plugin.yaml, `__init__.py`, `onboarding.py`, plus bundled `cv_toolkit` validators). It writes files only; it never changes live Hermes config or global memory. The plugin activates only after explicit, separate opt-ins:

1. **Project plugin discovery**: Hermes scans `.hermes/plugins/` only when project plugins are enabled — set `HERMES_ENABLE_PROJECT_PLUGINS=1` (docs use `true`) before launching Hermes.
2. **Enable/trust**: run `hermes plugins enable resume-toolkit` (or the equivalent enable/trust command for the installed version) and review the plugin at `ROOT/.hermes/plugins/resume-toolkit/` first; the toolkit runs no trust command itself.

Restart Hermes from the exact workspace root after installing skills or enabling the plugin.

The hook is scoped and advisory:
- It supports only a **dedicated CLI process launched at the exact workspace root**; it compares process cwd to the plugin root and stays **silent** when they differ. **Hermes desktop and gateway processes are not certified.**
- It returns `pre_llm_call` user context each turn, routing the agent to the workflow determined by the read-only `cv onboard --workspace ROOT` classifier (`experience-capture` for capture/interview/import, `application-materials` when ready, etc.).
- It is **advisory routing, not a sandbox**: structural validity does not prove factual truth, and approval/release is never asserted. It reads only structural records, never candidate prose.

Verify in a fresh, dedicated CLI session at `ROOT` that the plugin and the four skills are listed, then run a synthetic job-to-preview scenario. Do not claim production acceptance from fixture records.

## Other hosts and manual loading

Give the host `AGENTS.md` and the full path to `skills/application-materials/SKILL.md`, or to its installed copy. Ask it to read the linked references. Explicitly state the private workspace and installed `cv` executable. File access, conversations, delegation, browsing and artifact inspection are supplied by the host. If one is unavailable, report the missing capability and continue only the supported preview stages.

## Acceptance evidence

Automated tests check distribution consistency, reference resolution and installation without overwrites. A wheel installation should also be exercised outside the checkout. A manual agent scenario can prove that the instructions guide actual tool use, but does not prove native discovery in another host.

To verify native discovery, start a fresh session in the chosen scope, confirm the four skills in its index/menu, load application-materials and one linked reference, and run a synthetic job-to-preview scenario. Preserve actual host/version, scope and tool outcomes in private local verification notes. Do not use fixture review records to claim production acceptance. No global host configuration, trust or paid provider calls are changed by the installer.
