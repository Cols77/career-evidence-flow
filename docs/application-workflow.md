# Application workflow

Start with an AI host that can read and write files, run the `cv` helpers and communicate with the candidate. Ask it to use [application-materials](../skills/application-materials/SKILL.md). The host supplies the intelligence: interviewing, understanding the job, drafting and reviewing. The helpers run locally and require no model API key; this does not constrain the host to offline operation.

## 1. Capture the candidate

Use [experience-capture](../skills/experience-capture/SKILL.md) to turn the user's actual documents and answers into a private source registry and canonical evidence. Keep ownership, uncertainty, project maturity and publication restrictions. Existing evidence should prevent repeated interviews. Unknown or declined answers remain explicit gaps. Corrections preserve history and supersede obsolete claims.

Create an ordered projection from publishable evidence, then run `cv validate-evidence --workspace ROOT` and `cv validate-projection --workspace ROOT`. A blank workspace has no candidate claims; synthetic example profiles must never become a real candidate's record.

## 2. Understand the entire job

Read the full supplied posting, including minimum/preferred requirements and application instructions. A host with browsing tools may retrieve a user-supplied URL and save the retrieved text with its URL and retrieval time. If retrieval is unavailable or incomplete, ask for the full text and report incomplete extraction. The Python command does not fetch URLs.

Freeze that text with `cv create-application`. Persist employer policy **before** drafting: resume and cover letter are the default, but a no-letter instruction selects resume only. AI-use restrictions, plain-text instructions and custom length limits require explicit host handling. Stop AI drafting if it is forbidden; do not assume local rendering authorizes an AI-written application.

The host writes a readable job extraction and maps each requirement to evidence using confirmed, transferable, project_or_course_only, unsupported or unknown. A local prototype cannot satisfy professional production deployment. Job text supports company facts, never candidate facts. Use only source excerpts that occur in the frozen text; mark extraction complete only after checking the whole posting.

## 3. Assess opportunities and ask focused questions

Before substantive drafting, compare the key JD needs with the actual profile and prior answers. This strengthening assessment is required even for an existing resume. Identify the few missing details most likely to improve evidence selection, specificity or fit; ask at most three incisive questions per exchange only when useful. Do not run a generic interview, repeat saved/declined questions or insert an item just because its technology matches a keyword. A profile that already answers the useful questions needs a referenced no-question conclusion, not a token interview. Pure formatting corrections do not reopen the assessment.

For a relevant experiment, consider its problem, personal contribution, evaluation and result or learning. A qualitative/negative finding, limitation or decision enabled can matter as much as a metric; never invent one. Record the JD/evidence reasoning and question dispositions in private output notes for reviewers. When an unanswered material opportunity exists, wait before dependent drafting or eligibility/core-fit decisions; urgency or silence is not a waiver. A noncritical item may remain explicitly pending and excluded while other sufficient confirmed evidence supports independent drafting. Unattended runs without a permissible disposition may continue preparation, not silently finish the interview. This is host-agent policy, not a machine-enforced hook/CLI gate.

Persist actual answers with `cv answer`, including their registered source and timestamp. Add reusable facts to canonical master evidence, then update the selected projection before resolving an answered fact as retained or updated.

Unknown and declined outcomes need an explicit omit/gap disposition. They should allow honest drafting to continue. Unknown motivation means a provisional letter with that gap reported, rather than invented enthusiasm. Employer no-letter instructions remove the motivation question entirely. Answers already supported by current evidence need no new interview.

## 4. Draft the requested documents

Write the resume from selected evidence, using the job's language only where its meaning matches the candidate's actual experience. Write the cover letter, when requested, from the final resume, genuine answers and documented company facts. Keep a readable claim-to-source working map for reviewers, including identity, dates, skills, bullets and every factual letter subclaim. Current code does not enforce exhaustive maps or semantic entailment.

Select from the complete corrected master profile to maximise useful JD-relevant depth and breadth within the effective page limit. Compare concrete methods, ownership, delivery and outcomes across distinct capabilities; prioritise stronger supported contributions over repeated generic text or weak keyword matches. Record important inclusion/omission decisions, preserve readability, and keep unknown results out of the document. A noncritical item with a pending question can be deferred explicitly while unrelated supported work continues; do not invent a resolution or assume permission to use its missing facts.

Order professional experience newest to oldest, both between employers and among roles within each employer. Ongoing roles come first; completed roles sort by end date, then start date, newest first. Ongoing ties use original start date. Preserve explicit overlaps/resumed intervals and source-supported date precision; do not invent dates or imply sequential tenure. Page continuations preserve the same sequence. Prioritise relevant bullets within roles rather than moving older completed roles above newer work. See the skill's drafting reference for exceptions and ambiguous dates.

Use [the schema and command guide](workflow.md) and the skill's supporting references for the exact current file formats. There is no command that generates prose: the host agent writes it.

## 5. Review and revise

Use the reusable CLI instead of per-application preparation/rendering scripts:
`cv application-context --workspace ROOT --application applications/SLUG` validates
and locates inputs without drafting. After the host writes supported Markdown,
`cv build-application --workspace ROOT --application applications/SLUG --output outputs/SLUG/r01`
builds policy-selected previews, runs checks and saves a frozen input/review bundle.
Add repeated `--include` paths for actual supporting sources, earlier answers and
working notes. Run `cv verify-bundle --workspace ROOT --bundle outputs/SLUG/r01/bundle.json`
before review and handoff. These hashes check selected-file freshness only; the
host still establishes source completeness and actual review. See the installed
application-materials drafting reference for styles, page images and limitations.

Assign actual independent agents the relevant review skill and exact draft, evidence, job, policy and source inputs. Group work into evidence/job, voice/consistency and visual/artifact packets; keep each rubric angle visible. A reviewer names unsupported wording and proposes bounded corrections; the author applies them and requests another review of changed inputs. Limit repair to two rounds, then return unresolved findings.

Require explicit checks of the strengthening assessment and actual answer/disposition sources, evidence value of strategically relevant experiments, and reverse chronology in both source and rendered reading order. Skipping an identified material question without a disposition and misordering roles are concrete findings, even when individual statements are true. Do not fail an honest experiment solely for lacking a metric.

Run deterministic checks, render current Markdown to HTML/PDF and inspect the actual outputs. A successful text check cannot replace visual review. If the host cannot inspect artifacts or create independent reviewers, label that review unavailable. Never fabricate agent identities, review runs or an approval record.

Inspect page balance explicitly: compare content endpoints/bottom gaps and adjacent-page density. Repair avoidable early manual breaks instead of accepting a large blank area solely to preserve a section boundary. `cv check` provides a positioned-text `layout_audit`; its review signals require actual visual inspection and repair or a specific false-positive explanation even if the ordinary check status is pass. Text geometry is approximate and does not prove painted-area coverage, clipping or design quality.

## 6. Return previews and remaining decisions

Give the candidate the requested preview files, a truthful fit/gap assessment and unresolved review findings. Current `cv status` reports `draft_only` and `release_available: false`. Authenticated review records, automatic dependency invalidation, exhaustive claim-map enforcement and copying immutable reviewed bytes are still implementation work. Do not describe the previews as certified or submission-ready.

For host loading, see [agent hosts](agent-hosts.md). For the distinction between semantic review and release enforcement, see [review and release](review-and-release.md).
