# Start from one repository

Resume Toolkit contains the evidence database helpers, resume and cover-letter
workflows, all styles, fictional examples and adapters for Codex, Claude Code
and Hermes. You need Python 3.11+, your configured AI host, and Chrome/Chromium
for PDF output. No other resume repository or candidate-specific runner is needed.

## Install and bind your profile

From the cloned repository on Windows:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install .
.venv/Scripts/cv setup user-profile --host all --project-root .
.venv/Scripts/cv doctor --workspace user-profile --host all --project-root .
```

On macOS/Linux use `python3` and `.venv/bin/python` / `.venv/bin/cv`. Select
`--host codex`, `claude` or `hermes` if you only use one host. Always use this
environment's executable; an unrelated global `cv` can load an older package.

Open the repository root in your host and read the generated local
`RESUME_TOOLKIT.md`. It identifies the interpreter, project root and private
data workspace. Setup preserves existing candidate records and instructions;
it refuses conflicting skills or a different existing project binding.

The directory layout is:

```text
resume-toolkit/
  src/, skills/, docs/, tests/   shared toolkit
  .venv/                        ignored Python environment
  user-profile/                 entire folder ignored
    cvtool.toml                 standard workspace configuration
    profile/                    evidence.json, registry.json, projection.json
    intake/                     original source material
    applications/<job>/         job, answers, requirements and drafts
    outputs/<job>/<revision>/   generated documents and review artifacts
  RESUME_TOOLKIT.md             ignored local startup guide
  .local/resume-toolkit/        ignored project-to-data binding
```

Back up `user-profile/` separately. Git cloning restores the toolkit and its
fictional examples, never your private data. An external workspace is also
supported: `cv setup /private/my-profile --host all`, without `--project-root`.
See [deployment](deployment.md) for wheel installation without a checkout.

## Capture experience and prepare an application

Ask your host:

> Read RESUME_TOOLKIT.md and run its onboarding command. Use my configured
> private profile. Capture or import my actual experience, preserve sources and
> uncertainty, then use application-materials for the full job description I
> supply. Obtain independent resume and cover-letter reviews when available and
> inspect every rendered page. Report what actually ran.

`cv onboard --workspace user-profile` is read-only. A blank workspace routes to
`experience-capture`; a populated valid one routes to `application-materials`.
The host persists real answers with provenance and selects supported evidence.
Synthetic examples are never candidate facts. To try the packaged fictional
resume separately, run `cv gallery --output outputs/demo --format both`.

The host coordinates interviews, drafting and actual independent reviewers.
The Python commands validate records, save answers and render/check previews.
Hooks provide context; they do not write profile facts automatically. Current
tools do not authenticate reviews or provide a guarded submission release.

## Optional host hooks

After inspecting the adapter, run the installation for your chosen host:

```text
cv install-hooks --workspace user-profile --project-root . --host codex
cv install-hooks --workspace user-profile --project-root . --host claude
cv install-hooks --workspace user-profile --project-root . --host hermes
```

Use the pinned environment's `cv`. Hooks install at the project root and target
the bound child profile. Installation does not activate trust, change global
settings, or prove native execution. Restart the host after installation.

- **Codex:** inspect and trust the definitions in `/hooks`; check host feature
  availability. Its adapter supports advisory routing and explicitly recorded
  lifecycle checkpoints. See [Codex workflows](codex-workflows.md).
- **Claude Code:** inspect `.claude/settings.local.json` and the bundled runner.
  `SessionStart` and `UserPromptSubmit` supply advisory routing; they do not
  restore Codex checkpoints. Existing unrelated settings and hooks are preserved.
- **Hermes:** inspect the plugin, opt into project plugins using
  `HERMES_ENABLE_PROJECT_PLUGINS=1`, and enable/trust it through your installed
  host. Project skills also require trust on supported versions. Run a dedicated
  CLI process at the exact project root. Desktop/gateway routing is unverified.

See [host setup](agent-hosts.md) for commands, scope and acceptance checks. If
discovery is unavailable, explicitly read the installed skill and references
from the project root, then pass the same data workspace to every command.
Report manual fallback accurately; do not claim native orchestration from file
installation alone.
