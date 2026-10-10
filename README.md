# Resume Toolkit

An offline Python toolkit for owner-supplied candidate evidence and application document previews. This repository contains synthetic examples and fresh history. Keep real profiles, answers and outputs in a separate private workspace.

Requires Python 3.11 or newer. PDF previews additionally require a local Chrome/Chromium installation. No API key, hosted model or provider call is required.

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[test]"
.venv/Scripts/cv init ../candidate-demo --example developer
.venv/Scripts/cv validate-evidence --workspace ../candidate-demo
.venv/Scripts/cv validate-projection --workspace ../candidate-demo
.venv/Scripts/cv render --workspace ../candidate-demo --source resume.md --output outputs/resume.html
.venv/Scripts/cv check --workspace ../candidate-demo --document outputs/resume.html
.venv/Scripts/cv render --workspace ../candidate-demo --source letter.md --output outputs/letter.html --kind cover_letter --style letter
.venv/Scripts/cv check --workspace ../candidate-demo --document outputs/letter.html --kind cover_letter
```

The second example is `--example researcher`. Both people and their background are synthetic. To start without fixture claims, use `cv init ../my-private-workspace --name "Your supplied name"`. The empty evidence record intentionally does not validate until actual evidence has been captured. Init refuses nonempty destinations and has no force option.

To create PDF previews, use `--format pdf --output outputs/resume.pdf`. HTML is regenerated from the current Markdown for every PDF request. Rendering uses packaged local CSS, rejects images and raw HTML, and permits ordinary inert hyperlinks. It performs no network retrieval.

Freeze the full supplied job text in a workspace-relative UTF-8 file:

```powershell
cv create-application --workspace ../candidate-demo --slug sample-role --job job.txt --company "Example Organization" --title "Developer"
cv status --workspace ../candidate-demo --application applications/sample-role
```

The application begins with `extraction_complete: false`, an explicit effective policy and empty requirements/questions. A host agent or person supplies the extraction and truthful evidence mappings. Job text never establishes applicant facts. Unknown and unsupported requirements are retained as gaps. Actual answers are stored in the questions record with provenance; explicit corrections retain their history. See [the workflow](docs/workflow.md) for schema and command details.

```powershell
cv install-skills --workspace ../candidate-demo --host codex
```

Four packaged host skills cover evidence capture, application drafting, resume review and cover-letter review. `--host claude` and `--host hermes` select their workspace skill locations. Existing skills are never overwritten. Installation reports that runtime discovery is unverified; restart/reload your host and confirm its actual skill discovery. File creation alone is not host acceptance.

Implemented: workspace confinement, canonical evidence/source registry, ordered projections, frozen job manifests, requirement/question validation, answer persistence, generic HTML/PDF previews, ATS/letter checks, synthetic examples, packaged skills and an external-denylist privacy scanner. Optional JEV adapter code is retained for offline validation tests; the generic CLI does not enable or invoke it.

Unfinished: exhaustive document claim maps and semantic entailment, authenticated independent review records, dependency-complete invalidation, two-round enforcement, immutable reviewed-byte release and genuine end-to-end host acceptance. No current command certifies approval, freshness of declared evidence fingerprints, or submission readiness. `cv status` always reports draft-only readiness. This is a usable foundation for further development, not completion of the full application workflow.

Run tests with `python -m pytest -q`. Before committing or sharing, run the scanner with an external private denylist and manually inspect the proposed file allowlist. See [privacy checks](docs/privacy.md). This repository currently provides no open-source license; it has not been published to PyPI.
