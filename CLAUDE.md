# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Resume Toolkit

Read and follow [AGENTS.md](AGENTS.md); it holds the workflow and privacy rules and wins over this file. Application work starts with `/application-materials`; experience capture uses `/experience-capture`; opportunity screening uses `/job-search`. Run separate reviewers with `/resume-review` and `/cover-letter-review` when delegation is available.

The public name is Career Evidence Flow; the distribution is `resume-toolkit`, the package is `cv_toolkit`, the command is `cv`. The pinned interpreter for this checkout is `.venv/Scripts/python.exe` (see the Git-ignored `RESUME_TOOLKIT.md`); the real data workspace is the Git-ignored `user-profile/`.

## Commands

```powershell
.venv/Scripts/python -m pip install -e ".[dev,visual]"   # visual = PyMuPDF page images; PDF also needs local Chrome/Chromium
python -m pytest -q                                      # full suite (pythonpath=src, testpaths=tests from pyproject)
python -m pytest tests/test_render.py -q                 # one file
python -m pytest -q -k "projection and not cli"          # by name
python tools/sync_skills.py                              # regenerate skill copies from skills/
python tools/sync_skills.py --check                      # CI-style staleness check; run after any skills/ edit
python -m cv_toolkit.cli gallery --output outputs/resume-gallery --format both   # all resume styles on the fictional showcase profile
python tools/verify_installed.py                         # synthetic end-to-end check of installed package, hosts and previews
python tools/check_shareable.py --repo . --denylist ../private/denylist.json --mode staged   # before any public commit; denylist lives outside the repo
```

Every `cv` subcommand except `init`, `setup`, `doctor` and `gallery` takes `--workspace ROOT`, and every file argument is workspace-relative. Commands print one compact JSON object with `status` `ok` or `invalid` and exit 2 on `invalid`; validation details are deliberately generic in the output, so read the raised `ToolkitError` in tests rather than the CLI message. No `cv` command calls a model or needs an API key.

Skills are authored only in `skills/<name>/`; `.agents/skills/` (Codex), `.claude/skills/` (Claude Code) and `src/cv_toolkit/assets/skills/` (wheel) are byte-for-byte generated copies. Never edit the copies.

## Architecture

**Division of labour.** The host agent interviews, extracts requirements, selects evidence, writes Markdown and coordinates reviewers. Python only validates records, persists them atomically and renders/checks documents. Validation output is never approval; every rendered document is a preview.

**Record chain (one direction, each stage validated against the previous).**

1. `evidence.json` + `registry.json` (`evidence.py`): items of kind identity/experience/project/education/training/award/skill/language/preference, each holding claims with a status and source IDs that must exist in the registry. Only confirmed/approximate claims with allowed publication are "publishable"; uncertain, excluded and superseded claims stay stored but unselectable.
2. `projection.json` (`projection.py`): ordered sections that select publishable claims from selected items. It cannot rewrite evidence.
3. `applications/SLUG/` (`application.py`): `create-application` copies the projection, freezes the full job text with its SHA-256 (reload fails if the bytes change), and initialises `requirements.json`, `questions.json`, `answers.json` and `policy.json`. Requirement statuses with positive evidence need publishable claim IDs; `source_text` must occur verbatim in the frozen job text. Answers persist once in `questions.json` with provenance; changes need `--correction` and keep history (`questions.py`).
4. `outputs/SLUG/rNN/` (`application_tools.py`): `build-application` renders ATS and branded resumes plus letter, runs checks, and writes `bundle.json` with hashes of every selected input, package asset and artifact. `verify-bundle` later detects drift before review or handoff.

**Shared record plumbing** lives in `records.py` (strict JSON decode rejecting duplicate keys and constants, path confinement to the workspace, atomic writes) and `workspace.py` (`cvtool.toml` with `[profile]`, `[paths]`, optional `[ats]`; all paths confined under the workspace, Windows-safe export names). Reuse these rather than adding ad hoc JSON or path handling. Error types are `ToolkitError` subclasses (`WorkspaceError`, `EvidenceError`, `DeploymentError`, `WorkspaceBindingError`); `cli.py` maps them to the JSON status.

**Rendering and checks.** `render.py` turns Markdown into HTML through `assets/template.html` plus one packaged style (resume styles `ats`, `branded`, `modern`, `minimal`, and `letter`; CSS in `assets/`), validates the markup, and produces PDF through headless local Chromium. `ats.py` and `letter_check.py` extract text and report heading/phone/page/word findings without echoing contact data. `page_layout.py` (PyMuPDF) reports page balance and `artifact_audit.py` reports layout signals; these are observations for the agent to confirm against page images, not pass/fail gates.

**Host integration.** `bootstrap.py` creates workspaces (`init`, including the fictional `showcase`, `developer`, `researcher` examples in `assets/examples/`) and installs skills; `deployment.py` (`setup`, `doctor`) and `host_installation.py` (`install-agent`) manage per-host skill and hook files, the `.local/resume-toolkit/project.json` binding and ignore-rule checks. `onboarding.py` classifies a workspace (empty, synthetic, real, malformed) and returns which skill to load. `claude_hooks.py` and `codex_hooks.py` are advisory SessionStart/UserPromptSubmit style hooks that inject routing context and record `workflow-checkpoint` fingerprints; they never save answers, gate work or prove a review happened. `jev_review.py` is an optional, explicitly authorised external review transport and the only module that can call a provider.

## Testing conventions

Tests use synthetic data only (the packaged examples or `tmp_path`); never point a test at `user-profile/`. Scratch directories named `.tests-*/` and `outputs/` are Git-ignored and may be used for manual runs. Tests for hook, installer and host-discovery behaviour exercise real files under `tmp_path` because unit tests alone cannot show a host loaded a skill; for changed interview, drafting or review behaviour also run a synthetic agent scenario (see CONTRIBUTING.md).

## Privacy guards worth knowing before editing

`user-profile/`, `outputs/`, `.local/`, `.codex/`, `.hermes/`, `.claude/hooks/`, `.claude/settings.local.json`, `RESUME_TOOLKIT.md` and all `*.pdf`/`*.png` are Git-ignored and must stay so. Generated documents never belong in commits. Check error messages and check output do not echo candidate contact data. See [docs/privacy.md](docs/privacy.md) for the pre-publication denylist and allowlist procedure.
