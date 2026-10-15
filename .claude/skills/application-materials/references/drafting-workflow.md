# Host drafting and review workflow

## Inputs and working files

Read workspace identity/contact choices, canonical evidence and registry, application projection, frozen complete JD, requirement mappings, actual question answers and effective employer policy. Resolve real contradictions before publication. Skills work with existing `cv` commands; `cv --help` and each command's `--help` are authoritative for syntax.

Draft in application-specific source paths recorded in `application.json`, normally `applications/SLUG/resume.md` and `applications/SLUG/cover-letter.md`. Preserve historical/final originals and other applications. Use revision-specific outputs such as `outputs/SLUG/r01`. Ordinary authorized draft edits and repairs do not require repeated approval.

Put every generated PDF, HTML, page image and extracted-text file beneath the workspace's configured `[paths].outputs` directory. `cv init` creates `outputs/` and a matching `.gitignore` rule. For an existing workspace or custom output path, ensure that directory's contents are ignored before rendering; use `git check-ignore` when the workspace is in Git and check that generated files are not already tracked. Keep editable application sources separate from generated outputs. Never place real candidate files in the toolkit checkout.

## Resume

Choose sections and ordering for the role and the person's actual background. Do not force training, awards or a summary when they add no supported value. Use actual supplied identity/contact facts, dates, degrees and availability. The default workspace name is not verified identity.

For each summary, skill and bullet, record a working support note with source unit, factual subclaims, evidence IDs, ownership, maturity and limitations. This is an agent-authored workpaper, not an authenticated toolkit claim map. Existing `resume_claims`/`cover_letter_claims` manifest paths reserve future functionality; do not fill them with an invented production schema.

Select truthful actions and supported context/outcomes. A local prototype is not a production deployment. A team result is not personal sole ownership. Approximate values remain approximate. Coursework demonstrates coursework, not commercial experience. Mention tools only where evidence establishes their actual use. A listed skill needs evidence and visible same-document proof; otherwise omit it or record a specific unresolved finding. Do not invent an exception approval.

Use JD keywords only when their meaning matches the candidate's actual experience. Explain acronyms on first relevant use and ensure the owner understands the terminology. Apply the shared [voice and artifact review](voice-and-artifacts.md): load private writing preferences, edit for clarity and recheck factual scope before rendering. These criteria also apply to the cover letter.

Apply its action-led, one-contribution-per-bullet review to every resume bullet. Keep labelled skill and education inventories outside bullet lists. Put professional links in the same contact paragraph as the location, phone and email, above the header divider; let the row wrap naturally on small screens and inspect the final PDF for spacing.

## Cover letter

Use the final resume and actual application answers. Connect one or two supported experiences to concrete employer needs, without retelling every resume bullet. Company facts require the frozen JD or an actual checked source. Candidate motivation requires an actual answer; do not infer enthusiasm from the JD or fabricate admiration, a long-standing passion or company familiarity.

If motivation is unknown, a provisional opening can state only the application purpose and supported contribution. Keep the gap visible in work notes, omit unsupported enthusiasm and continue a neutral draft. Ask a motivation question only when the answer materially improves a requested letter. A no-letter employer instruction removes the letter deliverable. A prohibited AI-use rule prevents AI-generated application material, even though renderer commands would technically run.

## Rendering and checks

Save the complete effective policy as `applications/SLUG/effective-policy.json`; preserve the matching manifest policy. Example commands use existing functionality:

```text
cv render --workspace ROOT --source applications/SLUG/resume.md --output outputs/SLUG/r01/resume-ats.html --style ats
cv render --workspace ROOT --source applications/SLUG/resume.md --output outputs/SLUG/r01/resume-branded.html --style branded
cv render --workspace ROOT --source applications/SLUG/cover-letter.md --output outputs/SLUG/r01/cover-letter.html --style letter --kind cover_letter
cv check --workspace ROOT --document outputs/SLUG/r01/resume-ats.html --policy applications/SLUG/effective-policy.json
cv check --workspace ROOT --document outputs/SLUG/r01/cover-letter.html --kind cover_letter --policy applications/SLUG/effective-policy.json
```

For PDF use the same source with a `.pdf` output and `--format pdf`. Chromium/Chrome is required. PDF generation regenerates HTML from current Markdown; it does not authenticate reviews or certify visual quality. Raw HTML, embedded images and active/resource markup are rejected. Keep links ordinary HTTP(S), mailto or fragments.

Resume visuals are packaged with the toolkit: `branded` (warm editorial), `modern` (navy sans-serif), `minimal` (monochrome serif), and `ats` (plain). Select the style within the employer's format constraints and the user's preferences. An italic-only paragraph immediately below an h3/h4 is its date/metadata row; an undated h3 such as Earlier Experience keeps the same group hierarchy. A standalone top-level `[pagebreak]` paragraph requests a print page break without raw HTML. For visual development, use `cv init ROOT --example showcase` or `cv gallery --output NEW_DIRECTORY --format both`; the packaged example is fictional and never evidence about the candidate.

HTML checks cannot establish final PDF pagination. If PDF or visual tooling is unavailable, explain which check was not exercised and retain preview status. Do not fabricate screenshots or label an unobserved artifact visually reviewed.

Review `artifact_audit` from the same `cv check` result as described in [voice and artifact review](voice-and-artifacts.md#final-artifact-observations); no separate audit command or detector service is needed.

## Independent review and finish

Use `resume-review` and `cover-letter-review`. Delegate to actual independent subagents through the host's available delegation tool, using fresh context and the real packet. One reviewer may cover several angles only with separate findings and verdicts. A self-check, fixture, simulated response or manually typed reviewer ID does not establish independence.

Apply supported repairs, update working support notes, render a new revision and rerun affected reviewers/checks. Changes to facts, answers, JD, policy, text, styles or artifacts invalidate related review notes; the host tracks this manually. Stop after two review/repair rounds and report remaining findings.

Return requested artifacts and a short account of evidence gaps, actual reviews, visual capabilities and remaining findings. Existing commands always yield previews. Authenticated claim maps, enforced review freshness and guarded exact-byte release are unavailable; independent review notes do not create submission authorization.
