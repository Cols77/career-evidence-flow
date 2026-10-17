# Evidence and interview reference

All examples below are synthetic schema demonstrations. They are never facts about the person requesting help. Preserve existing records, IDs and history; adapt structure only, using actual supplied facts.

## Start from the owner's workspace

`cv init ROOT` creates an empty workspace and placeholder display name. It does not discover an identity or supply achievements. Read `cvtool.toml`; `[paths].profile` controls the profile directory. Confirm the person's actual name and publication choices before placing identity/contact information in drafts. Email and phone are optional. Do not infer nationality, work rights, availability, pronouns, language level or relocation preference.

Read existing evidence and answers first. An empty evidence file is an intake starting point; evidence validation requires at least one actual item with a claim. Do not add a fictional item to make it pass.

## Evidence schema

Evidence `schema_version` is the string `"1"`; the other records use numeric `1`. IDs use lowercase letters/digits plus `.`, `_`, `-`, with at least two characters. Source IDs begin `source.`. Claim IDs are unique across all items.

The registry is a JSON list, often `profile/registry.json`:

```json
[
  {
    "source_id": "source.owner-answer",
    "kind": "owner_answer",
    "fingerprint": "synthetic-reference-only"
  }
]
```

For real work, allocate a durable source ID for an actual answer/document, record its actual origin and retain its evidence. A fingerprint is a supplied declaration; it does not authenticate a source. If an actual raw-byte hash is available, record it accurately. Never invent a document, source location or hash.

Synthetic evidence example, often `profile/evidence.json`:

```json
{
  "schema_version": "1",
  "candidate_id": "candidate.synthetic",
  "items": [
    {
      "id": "project.test-bench",
      "kind": "project",
      "label": "Class test bench",
      "claims": [
        {
          "id": "claim.test-bench",
          "text": "Built a local Python test bench for a class project.",
          "status": "confirmed",
          "publication": "allowed",
          "sources": ["source.owner-answer"],
          "ownership": "Personal implementation within a class team",
          "maturity": "Local prototype",
          "limitations": ["No production deployment or measured commercial outcome is supported."]
        }
      ]
    }
  ]
}
```

Each item has `id`, `kind`, `claims`; optional `label`, `attributes`. Kinds are `identity`, `experience`, `project`, `education`, `training`, `award`, `skill`, `language`, `preference`. Each claim has `id`, `text`, `status`, `publication`, nonempty `sources`; optional `ownership`, `maturity`, nonempty `limitations`. Optional language `attributes.proficiency` must come from supplied information. Keep dates, degrees, locations and contact facts supported as carefully as achievement bullets.

| Storage status | Treatment in drafts |
| --- | --- |
| confirmed | Publish only with allowed permission and supported wording. |
| approximate | Publish only with allowed permission; retain the approximation. |
| uncertain | Store for follow-up; cannot be selected for publication. |
| source_only | A supplied source mentions it, but candidate confirmation is missing; cannot be selected. |
| superseded | Retain history; cannot be selected. |

Publication `restricted` denotes confidentiality; `excluded` denotes material the owner does not want used. Neither changes whether a stored fact is known. Do not change permission to make a projection validate.

## Material interview

Prepare a short evidence inventory, then ask questions whose answers change the document. Useful prompts:

| Gap | Ask | Safe fallback |
| --- | --- | --- |
| Ownership | Which part did you personally implement, and which belonged to the team? | State participation without claiming leadership. |
| Maturity | Was this local, tested with users, deployed internally or operated in production? | Preserve prototype/coursework wording. |
| Outcome or learning | What changed, was demonstrated or learned, how was it checked, and what decision did it enable? Ask about measurements only where relevant. | After the question is answered, declined or explicitly skipped, prioritise stronger evidence or describe the work narrowly without inventing an outcome. |
| Skill | Where did you use it, and what can you explain or demonstrate? | Omit unsupported proficiency. |
| Award | Was the award individual or team-based, and what did it recognize? | Preserve team attribution. |
| Identity/contact | What name/contact details may appear in this application? | Leave unprovided contacts out. |
| Motivation | What about this role matters to you, based on your actual interests or experience? | Acknowledge the application purpose without invented enthusiasm. |

For application work, start from the key JD needs and the candidate's actual strongest evidence, not a checklist of missing keywords. A technically true experiment label may leave a valuable outcome or learning unexamined. Ask about its purpose, personal contribution, evaluation/observation and result only where those details could change the resume. Qualitative findings, failed approaches, limitations and decisions can be useful evidence; do not infer them or demand a numeric/business result. Do not automatically include an experiment merely because it names a relevant technology.

Reuse sufficient answers. Do not ask for every possible metric, mandate a training section, invent a language level or reopen a previously declined/resolved gap. Record why no useful question remains when existing evidence is sufficient; do not manufacture a question to satisfy the workflow. When a material strengthening question remains, wait for an actual answer or explicit instruction to skip/proceed before dependent drafting or eligibility/core-fit decisions. A noncritical item may remain pending and be explicitly excluded while independent drafting uses other sufficient confirmed evidence; exclusion is not an answer or waiver. In a headless run without a permissible disposition, list the pending questions and continue independent preparation, not the affected claims. Unknown/declined answers permit supported narrowing or omission once recorded.

## Actual answers and corrections

Application questions live in `applications/SLUG/questions.json`. Create question records through authorized JSON edits; there is no `cv add-question` command. Each `unlocks` ID must exist in that application's requirements. An answered question still needs a disposition if it is material. Application-specific motivation stays answer-scoped; it is not automatically a global preference.

Register the actual answer's source in the registry, then:

```text
cv answer --workspace ROOT --questions applications/SLUG/questions.json --question-id question.scope --text "ACTUAL SUPPLIED ANSWER" --source-id source.owner-answer --recorded-at ACTUAL_ISO_TIMESTAMP
```

Replace the uppercase placeholders with actual inputs. The timestamp must have a timezone. Do not use the example text as an answer. Identical repeats are idempotent; changed answers require `--correction` and preserve history.

If a correction changes a factual claim, mark the old claim `superseded`, add the corrected claim with provenance, and update selections and drafts. Keep genuine history. `cv resolve-question` records a disposition; it never writes canonical evidence. Resolution actions `update_evidence`/`retain_existing` require existing publishable claim IDs; `omit_claim`/`record_gap` require empty claim IDs and a nonempty rationale. Terminal unknown/declined states require the latter actions. Pending/answered states cannot carry resolutions. `answers.json` is reserved and must remain empty.

```text
cv validate-evidence --workspace ROOT
cv validate-projection --workspace ROOT
cv status --workspace ROOT --application applications/SLUG
```

These validate structure, references and frozen inputs; they do not establish entailment, source authentication or release approval.
