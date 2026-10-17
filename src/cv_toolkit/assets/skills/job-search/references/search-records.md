# Search preferences and records

These are agent-authored conventions using the existing evidence schema. There is no search engine, job-fit scorer or search-record validator in the CLI. `cv validate-evidence` validates canonical evidence structure and references, not employer truth, search completeness or these companion files.

## Canonical preferences

Read the configured profile path. Keep one `preference.job-search` item, kind `preference`, in `evidence.json`. Keep existing IDs if a workspace already has an equivalent item. Each actual preference has a normal claim with a registered owner-answer source, confirmed status and private publication boundary (`excluded` by default; use existing owner permissions). Preserve exact answer bytes under the private source directory, register their actual SHA-256 and origin, and update the readable master if the workspace maintains one. Do not overwrite registered source bytes. Corrections supersede old claims and add sourced replacements; repeat identical answers idempotently.

Registry entries accept only `source_id`, `kind` and `fingerprint`. Store origin, recorded time and retained source path in the source document or the workspace's existing private source catalog; do not add unsupported registry keys.

Use `attributes.job_search` for structured fields. Each field has `state` (`specified`, `no_preference`, `unknown`, `declined`), `value` (or null), `claim_ids`, and `strength` (`hard`, `soft`, `unspecified`). Strength is not inferred from a casual interest; preserve the owner's wording. Supported value conventions:

| Field | Value |
| --- | --- |
| role_families | List of roles or technical domains; distinguish interest from skills. |
| industries | Included/excluded industries, or explicit no preference. |
| role_mix | Hands-on, technical lead/project, people management priorities. |
| seniority | Requested levels; no preference is not eligibility for every level. |
| location | Allowed onsite/hybrid locations and remote hiring geography. |
| relocation | Explicit destinations/conditions, otherwise unknown. |
| employment_type | Permanent, fixed-term, contract, hours if supplied. |
| compensation | Amount, currency, comparison (e.g. greater_than), period and base/total-package basis. Leave unsupplied components unknown. |
| availability | Actual start/notice details, otherwise unknown. |

Known nationality/work rights/clearance are identity or evidence facts, not preferences. Reference their claim IDs in assessments without duplicating them as new owner answers. Excluded private facts may inform internal eligibility checks but must not be copied into public documents. Capture only necessary eligibility information, not passport/visa identifiers. A preference item may contain unknown fields without invented claims; do not create an empty claim merely to pass validation.

## Private search outputs

Create a new directory under the configured outputs path, such as `job-search/RUN_ID/`, containing `results.json`, `report.md` and `sources/`. Never overwrite historical runs. The structured report uses this shape (field descriptions, not candidate facts):

```text
schema_version: 1
run_id, checked_at: actual UTC ISO timestamp
preference_claim_ids: canonical IDs used
scope: confirmed criteria, provisional assumptions, pending questions
profile_snapshot: relative evidence path and actual SHA-256
jobs: list of job records below
limitations: unavailable sources/tools and incomplete checks
```

Each job record includes:

- `job_key`: employer plus requisition ID; canonical URL fallback. Retain alias URLs and merge duplicate discoveries, not separate opportunities.
- `employer`, `title`, `requisition_id`, `url`, `checked_at`, `availability` (`listed_open`, `closed`, `unverified`) and closing date if stated.
- `sources`: URL, checked time, source type (employer/ATS/aggregator), scope (JD/form/listing), relative captured evidence path and actual hash. Short excerpts or retrieval notes are enough; never label a summary as a complete raw snapshot.
- `description_complete`, `form_checked`, `access_limits`: distinguish full JD from snippets and anonymous initial form from later stages.
- `conditions`: location, work model, remote hiring countries/time zones, travel, employment type, pay, start date. Attach source references to known values; record unknowns explicitly.
- `eligibility`: each condition, employer source, candidate claim IDs, finding (`met`, `conflict`, `unknown`, `time_conditional`) and rationale. Do not disclose restricted facts outside the private report without authorization.
- `requirements`: essential/desirable label, source, candidate claim IDs, finding (`supported`, `transferable`, `stretch`, `unsupported`, `unknown`) and the actual gap. Absence of evidence is not proof of inability.
- `deliverables`: resume, cover letter and other items, each with status, scope and source; AI-use policy, screening questions and assessments when visible. Unknown form access cannot become optional or not required.
- `technical_fit`, `administrative_fit`, `preference_fit`: explanations, not numerical scores. Salary and work-rights uncertainty must remain visible.
- `disposition`: `pursue`, `clarify`, `stretch`, `exclude`, or `closed`; rationale and next action. `pursue` is a recommendation, never application authorization.

Maintain `PROFILE/job-search-index.json` as a small agent-owned companion: `schema_version: 1`, `jobs` entries with job key, canonical/alias URLs, first/last checked times, latest availability/disposition and a workspace-relative results path. Preserve history via output runs; do not overwrite an existing application or equate a lead with one. If the index conflicts with the current employer page, retain the history and record the new finding.

Before reporting, check referenced claims/sources exist, captured file hashes match, URLs and duplicate keys are consistent, and every required/admin conclusion has a source or is explicitly unknown. These are agent checks, not an authenticated release gate. Do not claim exhaustive market coverage. Application records remain owned by `application-materials` after selection.
