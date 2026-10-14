# Cover letter review rubric

High findings: invented candidate facts/motivation, confidential disclosures or contradictions. Medium findings: misleading contribution/scope, unsupported company knowledge, missing requested content, unreadable/clipped output or policy violations. Low findings: optional editorial polish. Ground severity in the actual defect.

| Angle | Inspect |
| --- | --- |
| Factual subclaims | Every experience, credential, tool, result, date, availability or identity assertion has actual publishable candidate support. Paragraph-level support is insufficient when one clause adds an unsupported fact. |
| Ownership and scope | Prototype/coursework stays prototype/coursework; team outcomes stay team outcomes. No unsupported production deployment, leadership, maturity, impact or precision. |
| Motivation authenticity | Is interest grounded in an actual answer? A JD's attractive wording is not the person's motivation. Unknown interest must not become a long-standing passion or admiration. |
| Company specificity | Are stated company facts actually sourced? Does the letter connect genuine contributions to employer needs? The company-swap test identifies genericness without authorizing invented knowledge. |
| Role contribution | Does the letter select useful supported examples rather than repeat every resume bullet? Are transferable skills described honestly, with project/course limitations where relevant? |
| Resume consistency | Compare with the current final resume: dates, titles, scope, claims, terms and motivation must not conflict. A changed resume invalidates this verdict. |
| Voice and concision | Apply the shared [voice and artifact review](../../application-materials/references/voice-and-artifacts.md) against current private writing preferences and authentic samples, where supplied. |
| Comprehension | Define acronyms when useful and check that the owner can explain claimed knowledge. Ask only actual material questions; never supply their answer yourself. |
| Employer policy | Is a letter requested? Are AI-use and format constraints respected? Resume-only/no-letter requirements override the default two-document workflow. CLI previews do not enforce submission constraints. |
| Visual/artifact | Observe every requested page. Interpret `artifact_audit` using the shared reference. Check typography, whitespace, clipping, signature placement, extraction, word limits, page limits and current-source correspondence. No visual tools means unreviewed visual status. |
| Freshness | Evidence, answers, JD, policy, letter text, styles, artifacts and final resume are current. Authenticated freshness/release is unavailable; stale notes must be marked manually. |

## Existing commands

Use current workspace-relative inputs and a complete standalone effective-policy JSON file:

```text
cv check --workspace ROOT --document outputs/SLUG/r01/cover-letter.html --kind cover_letter --policy applications/SLUG/effective-policy.json
cv check --workspace ROOT --document outputs/SLUG/r01/cover-letter.pdf --kind cover_letter --policy applications/SLUG/effective-policy.json
```

`cv render` with `--kind cover_letter --style letter` renders current source; add `--format pdf` with a `.pdf` output for PDF. Chrome/Chromium is required for PDF. HTML word/text checks can assist a review, but cannot establish PDF pagination or observed layout. Phone and headings are optional unless the real policy requires them.

If motivation is unknown, the host may retain a neutral provisional application purpose and supported contributions, noting the unresolved motivation separately. It must not fabricate enthusiasm to satisfy this rubric. Return concrete findings or no-findings observations per angle; never label the toolkit output approved, released or submission-ready.
