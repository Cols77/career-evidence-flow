# Resume review rubric

Use concrete observations and source references. Severity: high for unsupported/confidential factual claims or material contradictions; medium for misleading scope, missing material coverage, unreadable/clipped content or incorrect extraction; low for optional stylistic improvements. A label alone does not justify rewriting a supported fact.

| Angle | Questions and common defects |
| --- | --- |
| Whole-document support | Does each identity/contact/date/degree/location/award/summary/skill/bullet fact have actual candidate evidence? Check every subclaim, not only major bullets. Is evidence confirmed/approximate and allowed for publication? |
| Ownership and maturity | Does “led,” “owned,” “delivered” or “deployed” add unsupported ownership or production maturity? Preserve personal versus team contribution, coursework versus employment, prototype versus production, limitations and approximate values. |
| Profile consistency | Are dates, labels, role levels, tooling, scope and numbers consistent with canonical evidence and actual corrections? Superseded claims cannot reappear through old drafts. |
| JD fidelity | Were all source categories extracted? Are direct, transferable and project/course-only mappings honest? Could an unsupported credential or eligibility condition be inferred from phrasing? Company needs cannot prove candidate experience. |
| Skills coherence | Is a listed skill supported, and is proof visible in the same document? Distinguish unsupported, supported-but-not-shown and shown. An exceptional inclusion needs a specific recorded rationale, never a fabricated approval. |
| Skills selection | Does each entry name a useful capability, method or relevant tool at an appropriate level of detail? Assess this separately from evidence support. Routine artifacts, dataset names and minor steps usually belong in an experience bullet, unless role-specific expertise justifies listing them. Report exact entries to consolidate, move or omit; do not inflate their replacements into unsupported MLOps or deployment skills. |
| Bullet evidence | Are action, context and outcome understandable and supported? Avoid invented impact percentages, commercial outcomes or tool lists. An honest action without a metric is acceptable. |
| Bullet openings and focus | Does every resume bullet start with a supported action verb? Does it combine independently meaningful contributions that should be split? Keep methods, constraints and results of one contribution together; do not split solely by sentence, verb or tool count. Check each resulting bullet's evidence and ownership. Use labelled paragraphs or rows for skill/education inventories rather than forcing them into action bullets. |
| Summary quality | Does a summary add supported role-relevant information, rather than generic excellence claims? No summary is acceptable when it adds little. A headline is still a factual claim. |
| Voice | Apply the shared [voice and artifact review](../../application-materials/references/voice-and-artifacts.md) against current private writing preferences and authentic samples, where supplied. |
| Acronym comprehension | Is an acronym explained where useful? Can the owner actually explain the claimed work? Ask only a material unresolved comprehension question; do not invent their answer. |
| Visual readability | Inspect all pages of actual ATS and branded output: hierarchy, font size, clipping, whitespace, page breaks, orphan headings, bullet wrapping and links. Keep professional links with contact information above the header divider, with readable spacing. Never infer this from source Markdown. |
| Extraction and policy | Run checks on exact outputs; interpret `artifact_audit` using the shared reference. Compare actual PDF page count with effective policy. HTML checks have no reliable page count. Verify names/contacts and text order, without inventing mandatory headings or contacts. |
| Revision freshness | Are review inputs current, including corrections, answers and effective policy? Was a new render produced after edits? Manually stale old notes; current tooling has no authenticated closure or release gate. |

## Existing commands

Use actual workspace-relative paths:

```text
cv check --workspace ROOT --document outputs/SLUG/r01/resume-ats.html --policy applications/SLUG/effective-policy.json
cv check --workspace ROOT --document outputs/SLUG/r01/resume.pdf --policy applications/SLUG/effective-policy.json
```

The policy path is a standalone complete effective-policy JSON object, not `application.json`. For regeneration, the author uses `cv render` with current source and a fresh revision path. Check output is structural/extraction evidence, never factual entailment, visual proof or submission approval.
