# Local workflow and schemas

The Python package owns structural validation and local persistence. A person or host agent owns interviewing, job extraction, drafting, factual entailment and visual assessment. Validation output is not approval.

Workspace configuration uses `[profile]` display_name and optional email/export_name; `[paths]` profile, applications, styles and outputs; optional `[ats]` phone_pattern. Paths must remain beneath the explicit workspace. Generic rendering uses packaged styles rather than a repository checkout or arbitrary workspace CSS.

Evidence uses **string** `schema_version: "1"`, a candidate_id and items. Each item has id, kind and claims. Supported kinds: identity, experience, project, education, training, award, skill, language and preference. Claims have globally unique id, text, status, publication and source IDs; optional ownership, maturity and limitations are preserved. A source registry is a list of `{source_id, kind, fingerprint}` records. Confirmed/approximate claims with allowed publication can be selected. Stored uncertain, excluded and superseded claims remain stored and are not publishable. Fingerprints are opaque supplied declarations, not source authentication.

Projections use numeric `schema_version: 1`, id, label and ordered sections of `{id, label, item_ids, claim_ids}`. Optional headline, summary_claim_ids and skills `{name, claim_ids}` are supported. A projection must select publishable claims belonging to its selected items; it cannot rewrite the master evidence.

`cv create-application` copies a validated projection, freezes the full supplied job text, stores its actual byte SHA-256, initializes requirement/question records and saves an effective policy. Reloading fails if the frozen job bytes change. Default deliverables are resume and cover_letter, maximum pages two and one respectively, letter words zero through 450, and AI use allowed. Supply a workspace-relative `--policy` JSON object to override these defaults before drafting. Allowed AI-use values are allowed, restricted and forbidden. The schema records employer instructions; current preview commands are not a policy-enforced submission system.

Requirements use numeric schema_version and a requirements list. Each entry has id, text, priority (required/preferred/instruction), status (confirmed/transferable/project_or_course_only/unsupported/unknown), claim_ids and rationale. Optional source_text must actually occur in the frozen job text. Positive statuses need publishable evidence; unknown/unsupported entries cannot assert claims. Extraction completeness is supplied by the host and does not establish exhaustive coverage automatically.

Questions use numeric schema_version and a questions list. Each entry has id, prompt, reason, unlocks (requirement IDs), status and material. Statuses are pending, answered, resolved, unknown, declined and not_needed. Actual answers have text, source_id and recorded_at; resolutions have action, claim_ids and rationale. Actions are update_evidence, retain_existing, omit_claim and record_gap. Update/retain need valid publishable claims; omission/gap need rationale. Resolve does not invent or edit evidence for the owner.

```powershell
cv answer --workspace ROOT --questions applications/SLUG/questions.json --question-id question.scope --text "Actual supplied answer" --source-id source.owner --recorded-at 2026-10-10T00:00:00Z
cv resolve-question --workspace ROOT --questions applications/SLUG/questions.json --question-id question.scope --resolution resolution.json --status resolved
```

An identical answer is idempotent. A changed answer needs `--correction`; old answer history is retained. Actual answers persist once in questions.json, while answers.json is currently an empty reserved manifest record. After a correction, supersede the obsolete evidence claim explicitly and update projections/drafts. Automatic complete review invalidation is not implemented.

Checks accept an optional workspace-relative `--policy` JSON record. They report text/page/word issues without echoing candidate contacts. Headings and phone are optional. Each rendered document remains an unreviewed preview. Resume and letter review skills describe independent review expectations, but enforcement and exact-byte guarded release are future implementation work.
