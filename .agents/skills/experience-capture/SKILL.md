---
name: experience-capture
description: Use when candidate experience, projects, education, skills, identity or preferences need capturing or correcting, or material evidence is missing for a resume or cover letter.
---

# Experience capture

You are the interviewer and evidence editor. The owner supplies facts; Python validates and persists records. Start by reading [the evidence and interview reference](references/evidence-and-interview.md).

1. Locate the explicit private workspace and read its configuration, supplied evidence, source registry, existing answers and requested application. Use configured profile paths. If absent, create an empty workspace with `cv init ROOT`; obtain actual identity/contact choices before publishing them. The default name is a placeholder. Never initialize a real candidate from a synthetic example or overwrite their records with fixtures.
2. Inventory sufficient evidence before interviewing. Preserve experience, project, education, training, award, skill, language, preference and identity records. Ask only for missing information that changes eligibility, factual wording, attribution, publication permission or application motivation. Ask at most three focused questions per exchange; do not repeat answered or explicitly declined questions.
3. Distinguish personal contribution from team work, prototype from production, coursework from employment, and measured outcomes from guesses. Offer omission or narrower truthful wording when a metric, ownership detail or motivation is unknown. A JD describes employer needs and cannot prove candidate experience.
4. Persist actual supplied answers with source provenance once, using `cv answer` for application questions. Register the source first; never invent an answer to clear a checkpoint. Changed answers require `--correction`. Update canonical evidence separately and explicitly supersede obsolete claims; resolving a question does not update evidence automatically.
5. Keep the five storage statuses distinct: `confirmed`, `approximate`, `uncertain`, `source_only`, `superseded`. Publication permission is separate: `allowed`, `restricted`, `excluded`. Select only confirmed/approximate allowed claims, preserving limitations and approximate wording.
6. Validate with `cv validate-evidence --workspace ROOT`. When a question is resolved, use a supplied resolution JSON and `cv resolve-question`; unknown/declined require an omit/gap disposition. Revalidate projections and affected applications after changes.

Finish with persisted facts, answered questions, remaining gaps and the narrower wording they permit. If no person can answer now, return a concise material checkpoint and continue work that does not require the missing fact. Hand application drafting to `application-materials`.

Capture never approves a document or authorizes submission. Automatic review invalidation and authenticated release are unavailable; mark affected drafts/review notes stale yourself.
