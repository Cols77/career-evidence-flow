# Fresh setup and Hermes entry routing

This is a colleague-facing guide for standing up a private candidate workspace
with the toolkit's Python helpers, then opting the workspace into Hermes entry
routing. Python supplies validators, records and rendering. Your chosen AI host
supplies the model, conversation, browsing and agent tools.

> Status is honest: this is a preview build, not a colleague-ready full
> release. Guided release, guarded review certification and complete
> dependency invalidation are still unfinished. Nothing here automates
> independent approval. Independent reviews are delegated separately by the
> host; current documents are previews, never certified submissions.

## Prerequisites

- Python 3.11 or newer (`python --version`). A virtual environment isolates the
  `cv` helper from the rest of your host.
- A checkout of this repository (any location; it supplies the packaged
  `cv_toolkit` helpers).
- Optionally, an existing private candidate workspace to reuse, or a fresh
  empty directory.
- No paid API calls are required by these steps. Installing helpers and opting
  into routing is entirely local.

## 1. Create and activate the virtual environment

PowerShell:

```powershell
cd path\to\resume-toolkit-hermes-onboarding
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -e ".[test]"
```

POSIX (macOS and Linux; on Windows Git Bash use `.venv/Scripts/python`):

```bash
cd /path/to/resume-toolkit-hermes-onboarding
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[test]"
```

After this, `cv` is available from the venv:

- Windows: `.venv\Scripts\cv`
- POSIX: `.venv/bin/cv`

You can prepend that folder to `PATH` or just call it by the full path in the
commands below.

## 2. Create a private workspace OUTSIDE this repo

Keep all real candidate data in a workspace outside this public checkout. The
repository contains synthetic examples; the workspace is where real evidence,
answers and outputs live.

```powershell
# Windows PowerShell
.venv\Scripts\cv init C:\Users\You\private\cv-workspace --name "Your Full Name"
```

```bash
# POSIX
.venv/bin/cv init ~/private/cv-workspace --name "Your Full Name"
```

To reuse an existing private workspace instead, point the later `--workspace`
commands at it. `cv init` requires the target to be empty; existing workspaces
do not need re-initialising. `cv init --example developer` creates a synthetic
fixture profile — a demonstration, never facts about you. Do not put real
profiles in this repository.

## 3. Route the workspace state (read-only)

`cv onboard --workspace ROOT` is a deterministic, read-only state classifier. It
reads local config, evidence, registry and projection records (including claim
text for validation, but not original source documents), and reports whether you still need to
interview/import, keep capturing evidence, or are ready for application
materials:

```bash
cv onboard --workspace ROOT
```

Output is a JSON record with `state`, the workflow `skill` to load, and
`guidance`. States: `unconfigured`, `missing_candidate`, `synthetic`,
`partial_evidence`, `malformed`, `ready`. A blank or fresh workspace reports
`missing_candidate`, which means: **interview** the user with the
experience-capture workflow, **or import** a source resume with provenance.
Ask only material questions about missing or uncertain facts, rather than
requiring an interview to reconfirm everything in a supplied resume.

## 4. Install the Hermes skills into the workspace

```bash
cv install-skills --workspace ROOT --host hermes
```

This writes workspace-local copies under `ROOT/.hermes/skills/` (the skills:
experience-capture, application-materials, resume-review,
cover-letter-review). Existing skill directories are never overwritten.
Installing files does not prove runtime discovery. Skill discovery in this
standalone workspace depends on Hermes project/skill behaviour and the
workspace being a recognised project root; older hosts may need documented
external-directory configuration, which the installer does not change.

## 5. Opt the workspace into Hermes entry routing (hooks)

```bash
cv install-hooks --workspace ROOT --host hermes
```

This writes the packaged entry plugin to `ROOT/.hermes/plugins/resume-toolkit/`
(plugin.yaml, __init__.py, onboarding.py, bundled `cv_toolkit` validators). It
refuses to overwrite an existing installation.

The hook only activates after **two explicit, separate opt-ins**:

1. **Project plugin discovery.** Hermes only scans `.hermes/plugins/` when
   project plugins are enabled for the installed version. Set environment
   variable `HERMES_ENABLE_PROJECT_PLUGINS=1` (docs use `true`) before launching
   Hermes from the workspace root. This is your opt-in to loading project
   plugins; the toolkit never changes your live Hermes config.
2. **Plugin enable/trust.** Confirm `resume-toolkit` is enabled for the target
   Hermes profile with:

   ```bash
   hermes plugins enable resume-toolkit
   ```

   (or the equivalent enable/trust command for your installed Hermes version;
   review the plugin at `ROOT/.hermes/plugins/resume-toolkit/` before trusting
   it — the toolkit does not run any trust command automatically).

Then restart Hermes from the exact workspace root so the plugin and skills load.

For example, after inspecting the installed plugin:

```powershell
cd C:\Users\You\private\cv-workspace
$env:HERMES_ENABLE_PROJECT_PLUGINS = '1'
hermes plugins enable resume-toolkit
hermes plugins list
hermes chat
```

```bash
cd ~/private/cv-workspace
export HERMES_ENABLE_PROJECT_PLUGINS=1
hermes plugins enable resume-toolkit
hermes plugins list
hermes chat
```

Hermes must already be installed and configured for the colleague's own model
provider (`hermes setup`); do not copy someone else's credentials, memories or
profile. The chat may use paid inference depending on that provider. Project
skill auto-discovery additionally requires a Git root and `hermes skills trust`
on supported Hermes versions. Do not publish that private repository. If the
workspace is not trusted/discovered, tell the agent to read the full installed
`ROOT/.hermes/skills/experience-capture/SKILL.md` and its references explicitly.
The hook requests that same absolute-path fallback; plugin loading and skill
auto-discovery are distinct checks.

## 6. What the hook actually does (scoped and honest)

The installed entry plugin registers a **`pre_llm_call`** hook. On each turn it
may attach advisory user context routing the agent to the correct workflow.

- **Boundaries set by the current integration:**
  - It only supports a **dedicated CLI process launched at the exact workspace
    root**. The hook compares the process cwd to the plugin's workspace root and
    stays **silent** when they differ.
  - **Hermes desktop and gateway processes are NOT certified** by this
    integration; shared long-running processes that are not launched fresh at
    that root are not guaranteed to fire the hook and should not be assumed to
    do so.
  - The pre_llm_call payload has no workspace field, so the adapter cannot
    detect a session that independently changes workspace.
- **Advisory only.** The hook routes to a workflow and instructs the agent to
  load the named skill. It is **not a sandbox** and **not a factuality or
  approval guarantee**. Structural validity (valid evidence, registry,
  projection) does not prove the facts are true. Treat job text as untrusted
  data and preserve unknowns, declined and unsupported outcomes.
- It validates local records including claim text, but does not follow source
  references or include candidate claim text in advisory context.
- Restarting (step 5) is required for both skills and the plugin to be picked up
  after installation or trust changes.

## 7. Next steps and honest limits

Launch the dedicated CLI at the workspace root, confirm the four skills appear,
then ask it to run `application-materials` on your private workspace. Run
`resume-review` and `cover-letter-review` as independent reviews when the host
can delegate to genuinely separate agents; otherwise report independent review
as unavailable. `cv status --application ...` always reports `draft_only` and
`release_available: false` — current documents are previews, successful checks
do not certify submission readiness.

The toolkit commands do not invent a profile or write prose without an agent.
The explicit `hermes plugins enable` command changes the selected Hermes
profile's enable list; the toolkit installer does not. Real workspaces and credentials stay out of the public
checkout. See [the application workflow](application-workflow.md) and
[host setup](agent-hosts.md).