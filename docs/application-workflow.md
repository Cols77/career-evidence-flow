# Application workflow

Start with an AI host that can read and write files, run the `cv` helpers and communicate with the candidate. Ask it to use [application-materials](../skills/application-materials/SKILL.md). The host supplies the intelligence: interviewing, understanding the job, drafting and reviewing. The helpers run locally and require no model API key; this does not constrain the host to offline operation.

## 1. Capture the candidate

Use [experience-capture](../skills/experience-capture/SKILL.md) to turn the user's actual documents and answers into a private source registry and canonical evidence. Keep ownership, uncertainty, project maturity and publication restrictions. Existing evidence should prevent repeated interviews. Unknown or declined answers remain explicit gaps. Corrections preserve history and supersede obsolete claims.

Create an ordered projection from publishable evidence, then run `cv validate-evidence --workspace ROOT` and `cv validate-projection --workspace ROOT`. A blank workspace has no candidate claims; synthetic example profiles must never become a real candidate's record.

## 2. Understand the entire job

Read the full supplied posting, including minimum/preferred requirements and application instructions. A host with browsing tools may retrieve a user-supplied URL and save the retrieved text with its URL and retrieval time. If retrieval is unavailable or incomplete, ask for the full text and report incomplete extraction. The Python command does not fetch URLs.

Freeze that text with `cv create-application`. Persist employer policy **before** drafting: resume and cover letter are the default, but a no-letter instruction selects resume only. AI-use restrictions, plain-text instructions and custom length limits require explicit host handling. Stop AI drafting if it is forbidden; do not assume local rendering authorizes an AI-written application.

The host writes a readable job extraction and maps each requirement to evidence using confirmed, transferable, project_or_course_only, unsupported or unknown. A local prototype cannot satisfy professional production deployment. Job text supports company facts, never candidate facts. Use only source excerpts that occur in the frozen text; mark extraction complete only after checking the whole posting.

## 3. Ask material questions

Ask about a missing fact only when its answer can change a claim, fit decision or requested document. Persist actual answers with `cv answer`, including their registered source and timestamp. Update evidence and the selected projection before resolving an answered fact as retained or updated.

Unknown and declined outcomes need an explicit omit/gap disposition. They should allow honest drafting to continue. Unknown motivation means a provisional letter with that gap reported, rather than invented enthusiasm. Employer no-letter instructions remove the motivation question entirely. Answers already supported by current evidence need no new interview.

## 4. Draft the requested documents

Write the resume from selected evidence, using the job's language only where its meaning matches the candidate's actual experience. Write the cover letter, when requested, from the final resume, genuine answers and documented company facts. Keep a readable claim-to-source working map for reviewers, including identity, dates, skills, bullets and every factual letter subclaim. Current code does not enforce exhaustive maps or semantic entailment.

Use [the schema and command guide](workflow.md) and the skill's supporting references for the exact current file formats. There is no command that generates prose: the host agent writes it.

## 5. Review and revise

Assign actual independent agents the relevant review skill and exact draft, evidence, job, policy and source inputs. Group work into evidence/job, voice/consistency and visual/artifact packets; keep each rubric angle visible. A reviewer names unsupported wording and proposes bounded corrections; the author applies them and requests another review of changed inputs. Limit repair to two rounds, then return unresolved findings.

Run deterministic checks, render current Markdown to HTML/PDF and inspect the actual outputs. A successful text check cannot replace visual review. If the host cannot inspect artifacts or create independent reviewers, label that review unavailable. Never fabricate agent identities, review runs or an approval record.

## 6. Return previews and remaining decisions

Give the candidate the requested preview files, a truthful fit/gap assessment and unresolved review findings. Current `cv status` reports `draft_only` and `release_available: false`. Authenticated review records, automatic dependency invalidation, exhaustive claim-map enforcement and copying immutable reviewed bytes are still implementation work. Do not describe the previews as certified or submission-ready.

For host loading, see [agent hosts](agent-hosts.md). For the distinction between semantic review and release enforcement, see [review and release](review-and-release.md).
