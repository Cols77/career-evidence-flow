# Resume Toolkit

Generate a resume and cover letter with an AI agent, grounded in the candidate's real experience. The agent interviews you where evidence is missing, maps your background to the full job description, drafts the requested documents and coordinates independent reviews.

The agent workflows are the product entrypoint. Python supplies the evidence validators, application records and document renderer. Those helpers run locally without an API key; your chosen AI host supplies the model, conversation, browsing and agent tools.

## Workflows and skills

| Skill | Use it to |
| --- | --- |
| [application-materials](skills/application-materials/SKILL.md) | Run the job-to-resume-and-letter workflow, including material questions and review handoffs |
| [experience-capture](skills/experience-capture/SKILL.md) | Capture real experience with sources, ownership and limitations |
| [resume-review](skills/resume-review/SKILL.md) | Independently review evidence, job fit, voice, ATS output and layout |
| [cover-letter-review](skills/cover-letter-review/SKILL.md) | Independently review genuine motivation, company relevance, consistency and layout |

Read [the application workflow](docs/application-workflow.md) and [host setup](docs/agent-hosts.md). The canonical skills and their supporting references live in `skills/`. Generated repository copies live in `.agents/skills/` for Codex/Hermes and `.claude/skills/` for Claude Code. [AGENTS.md](AGENTS.md) is the generic agent entrypoint; [CLAUDE.md](CLAUDE.md) points Claude to the same workflow.

## Start with an agent

Install the package once (Python 3.11 or newer), then create a private workspace
with the complete skills for your host:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install .
.venv/Scripts/cv setup ../my-private-workspace --host codex
.venv/Scripts/cv doctor --workspace ../my-private-workspace --host codex
```

Use `--host claude`, `--host hermes` or `--host all` as appropriate. On macOS/Linux,
use `.venv/bin/python` and `.venv/bin/cv`. Open the private workspace in your AI
host, read its generated `RESUME_TOOLKIT.md`, and ask:

> Use application-materials. My private candidate workspace is ../my-private-workspace. Help me capture my actual experience, then tailor a resume and cover letter to the full job description I supply. Ask only questions that change the application, preserve unknowns and limitations, and run independent reviewers when available. Follow the employer's document and AI-use instructions.

The host reads the skill and references, writes the evidence and drafts, and invokes `cv` using the installed executable. A blank workspace intentionally has no candidate claims until real facts are captured. No command invents a profile or generates prose without an agent.

`cv setup` safely reuses a valid workspace and identical installed skills, preserving candidate data and existing instructions. Conflicting skill files require an explicit comparison and upgrade. The lower-level `cv install-skills` remains available. Installation does not prove runtime discovery.

See [portable installation and packaging](docs/deployment.md) for Windows/POSIX commands, wheel installation without a checkout, all three hosts, synthetic test workspaces and optional hooks. Host trust and provider configuration remain explicit. The toolkit produces reviewed previews; it has no authenticated release or submission gate.

## Try a synthetic example

To compare the packaged **Editorial**, **Modern**, **Minimal** and **ATS** resume designs using one fictional two-page resume:

```powershell
cv gallery --output outputs/resume-gallery --format both
```

Open `outputs/resume-gallery/index.html`. Use `--format html` without Chrome/Chromium. For an editable test workspace, run `cv init ../resume-demo --example showcase`. All styles, rendering logic and example data ship with this repository and its wheel. See [resume visuals](docs/resume-visuals.md) for setup, Markdown conventions and verification.

```powershell
cv init ../candidate-demo --example developer
cv validate-evidence --workspace ../candidate-demo
cv validate-projection --workspace ../candidate-demo
cv render --workspace ../candidate-demo --source resume.md --output outputs/resume.html
cv check --workspace ../candidate-demo --document outputs/resume.html
cv render --workspace ../candidate-demo --source letter.md --output outputs/letter.html --kind cover_letter --style letter
cv check --workspace ../candidate-demo --document outputs/letter.html --kind cover_letter
```

`--example researcher` provides a second synthetic background. Both are fixtures, never facts about you. PDF previews require local Chrome/Chromium; add `--format pdf` and use a `.pdf` output path. HTML is regenerated from current Markdown on every PDF request.

The host freezes supplied job text with `cv create-application`, maps requirements and persists real answers. See [schemas and executable commands](docs/workflow.md) for exact records, policy overrides, corrections and question dispositions. Unknown requirements remain gaps; a local project remains a local project. Resume and cover letter are the default, with employer instructions taking precedence.

## Current implementation boundary

The four agent skills include interview procedures, drafting steps, schema examples and independent review rubrics. The helpers validate evidence/source joins, projections, frozen job bytes, requirements and questions; persist answers and corrections; render HTML/PDF previews; and check document text and limits.

The full guarded release system remains unfinished: exhaustive claim maps, authenticated reviewer records, complete dependency invalidation, enforced repair rounds and immutable reviewed-byte release. `cv status` always reports `draft_only` and `release_available: false`. Files are previews; successful checks do not certify submission readiness. See [review and release](docs/review-and-release.md). Native host discovery and full host acceptance must be demonstrated separately from installing files or running tests.

Keep real profiles, answers and outputs outside this public repository. It contains synthetic examples and fresh history. Before publishing changes, run [privacy checks](docs/privacy.md) with an external private denylist and inspect the file allowlist. No open-source license has been selected, and this project is not published to PyPI.

For development: `python -m pytest -q`; check generated skill copies with `python tools/sync_skills.py --check`. Edit only `skills/` and regenerate with `python tools/sync_skills.py`. See [contributing](CONTRIBUTING.md).
