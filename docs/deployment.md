# Install for Codex, Claude Code or Hermes

Install one Python package, then set up a private workspace for your chosen host.
The package includes the four skills and their references, resume styles,
fictional examples, validators and renderer. It does not include candidate data,
model credentials or a model provider. Python 3.11 or newer is required;
Chrome/Chromium is required only for PDF rendering.

## Install the package

From a clone of this repository, create an isolated environment and install the
package normally. A development/editable installation and test dependencies are
not required for use.

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install .
.venv\Scripts\cv setup user-profile --host all --project-root .
.venv\Scripts\cv doctor --workspace user-profile --host all --project-root .
```

macOS/Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/cv setup user-profile --host all --project-root .
.venv/bin/cv doctor --workspace user-profile --host all --project-root .
```

Use `--host claude`, `--host hermes` or `--host all` with both commands. Keep this
environment installed and use it when running the workspace's helpers.
Activate it or add its executable directory to PATH if you want to type `cv`
without a full path. Your AI host must be installed and configured separately.

For a prebuilt distribution, replace `pip install .` with:

```text
python -m pip install /path/to/resume_toolkit-0.2.0-py3-none-any.whl
```

Use that environment's Python. The wheel needs no repository checkout after
installation. Pip still obtains the declared Python dependencies unless they
are already available. The project has not been published to PyPI; an unqualified
`pip install resume-toolkit` is not the installation route documented here.

## Use a neutral private workspace

The default clone layout uses Git-ignored `user-profile/` in this repository.
It owns `profile/`, `applications/<job>/`, `intake/` and
`outputs/<job>/<revision>/`. Its evidence, registry, projection and application
records use the same standard format as `cv init`; no personal adapter or second
repository is required. Do not put the master profile inside an employer's
application directory. Keep a separate backup of this ignored folder.

`--project-root .` installs host files at the repository root and binds them to
the selected child data workspace in ignored `.local/resume-toolkit/project.json`.
The generated local `RESUME_TOOLKIT.md` pins the interpreter and both roots.
Use its commands to avoid accidentally loading an older global `cv` installation.
Setup refuses silent rebinding; inspect the old local configuration before
deliberately replacing it. The data workspace must be the project root or a
contained child. Existing candidate records are preserved.

An external private workspace remains supported, including with a wheel and no
checkout: `cv setup /private/my-cv --host all`. Omit `--project-root` when data
and host files share that root. Verify ignore rules before adding real data.

`cv setup` initializes an empty directory, or reuses an existing valid toolkit
workspace while preserving its candidate records. Repeating setup with identical
installed skills is harmless. It preflights conflicting skills before installing
the requested hosts; it does not silently replace customizations. Existing agent
instruction files are preserved. Read the generated `RESUME_TOOLKIT.md` for the
exact startup procedure and fallback instructions.

`--name` applies only when initializing a workspace. `--example` requires a new
workspace; omit it when repeating setup on the same synthetic workspace.

For an intentional upgrade, compare the installed skills with the new package,
back up the affected skill directories outside their discovery directory, remove
only those confirmed old copies, then run setup again. Do not delete a private
workspace or profile to upgrade skills. The existing `install-skills` command
remains available for strict first-time installation.

For a test workspace containing **only fictional evidence**:

```text
cv setup ../resume-demo --host all --example showcase
cv doctor --workspace ../resume-demo --host all
cv gallery --output ../resume-demo/outputs/gallery --format both
```

Use `--format html` if no browser is installed. Synthetic records demonstrate
the toolkit; they must never be treated as evidence about a real candidate.

## Start the host in the project

| Host | Workspace skills | Invocation |
| --- | --- | --- |
| Codex | `.agents/skills/` | `$application-materials` or an explicit request to use it |
| Claude Code | `.claude/skills/` | `/application-materials` |
| Hermes | `.hermes/skills/` | `/application-materials` after project discovery/trust |

These paths follow the hosts' current documentation:
[Codex skills](https://learn.chatgpt.com/docs/build-skills),
[Claude Code skills](https://code.claude.com/docs/en/skills), and
[Hermes skills](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills/).
This integration targets local agent hosts with filesystem and command tools;
ordinary web chat is not an equivalent runtime.

Launch a fresh session from the project root (the checkout in the single-repo
layout). Confirm the four skills appear
and load one linked reference. Some hosts require a recognized Git project and
explicit trust. If needed, initialize a **private local** Git repository there;
the toolkit does not create a remote or publish candidate records. Hermes project
skill discovery requires inspecting the skills and explicitly running
`hermes skills trust` on supported versions. See [host setup](agent-hosts.md).

Give the host this first instruction:

> Read RESUME_TOOLKIT.md. Use its explicit private data workspace and pinned
> interpreter. Run the documented onboarding command and follow its returned skill.
> Capture or import my actual experience, then tailor the requested documents to
> the full job description. Use real independent reviewers where available and
> report which reviews and visual checks actually ran. Keep unknowns and limits
> explicit. Do not submit an application.

A blank profile routes to `experience-capture`; it is not an installation error.
If native discovery is unavailable, explicitly read the installed skill and its
references by absolute path. Report that fallback rather than claiming discovery.

## Diagnose installation and orchestration separately

`cv doctor` is read-only. It checks local workspace/package prerequisites and
installed skills, with actionable errors and warnings. Missing browser or host
executables, Git discovery prerequisites and a profile needing capture should be
interpreted separately from malformed data or conflicting skill files.

An installation check cannot establish native skill discovery, actual reviewer
delegation, visual inspection or automatic workflow restoration. The host supplies
these capabilities. Review notes must identify actual agents, inspected revisions,
pages and findings. Every skills entry needs both support and an editorial judgment
about its usefulness; matching words in evidence is insufficient.

Hooks are an optional next step:

```text
cv install-hooks --workspace user-profile --project-root . --host codex
cv install-hooks --workspace user-profile --project-root . --host claude
cv install-hooks --workspace user-profile --project-root . --host hermes
```

Run only the command for the host you intend to activate. Setup does not install
or trust hooks. Follow [Codex activation and execution evidence](codex-workflows.md)
or [Hermes opt-ins and scope](agent-hosts.md#hermes-entry-hook-routing-workspace-cv-onboard-route).
Claude Code's `SessionStart` and `UserPromptSubmit` adapters add advisory routing
to `.claude/settings.local.json`, preserving unrelated settings and hooks.
They do not save answers or restore Codex checkpoints. See
[host setup](agent-hosts.md#claude-code) for activation and scope. All adapters
are installed at the project root and explicitly bound to the data workspace.

Without actual lifecycle metadata, continue from the private records manually and
report automatic restoration as unverified. For reviewed revisions, snapshot all
consulted sources, including answers in earlier applications. A fresh snapshot
does not prove its completeness or that a reviewer ran. Documents remain previews;
neither installation nor hooks certify or submit them.

## Build a distribution

Maintainers can build the same installable artifacts using:

```text
python -m pip install ".[dev]"
python tools/sync_skills.py --check
python -m pytest -q
python tools/build_release.py --output dist/0.2.0
```

The destination must be new. It receives the wheel, source distribution,
`INSTALL.md`, linked usage documents under `docs/` and `skills/`, `SHA256SUMS`
and `release-manifest.json`. The installation guide and its local references can
be read without a checkout or network connection. Inspect the manifest and run the external
private denylist scan described in [privacy checks](privacy.md) before sharing.
Builds do not upload, publish to PyPI, create a GitHub release or select a license.

Install the wheel in a fresh environment outside the checkout, then run
`tools/verify_installed.py --output NEW_DIRECTORY --source-checkout CHECKOUT`
using that environment's Python from outside the checkout. The check exercises
all three hosts' setup files, synthetic records, HTML/PDF rendering and gallery
artifacts. It requires Chrome/Chromium. Its report explicitly leaves live host
discovery and agent orchestration unverified; those require real host sessions.
