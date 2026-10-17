# Focused evidence strengthening and experience chronology

## Scope and accepted direction

Integrate a required, brief JD-to-profile strengthening assessment into existing drafting and review. Ask only incisive questions with a concrete opportunity to improve the resume; do not mandate an interview, repeat saved answers, or add weak items just to match keywords. The owner clarified this direction on 17 October 2026. No new CLI approval mechanism or runtime gate is introduced.

Before substantive tailoring, compare the JD's key needs with current canonical evidence and actual answers. Identify the few missing details most likely to change selection, specificity or strength. Ask at most three focused questions per exchange when useful, and wait for answers or an explicit skip before drafting affected material. Record a concise assessment with evidence references and the question/disposition, or a justified no-question conclusion. A complete profile must not trigger a generic token interview. Pure formatting corrections do not reopen capture.

Experiments need investigation of their purpose, personal contribution, evaluation/observation and result or learning when relevant to the JD. Qualitative findings, negative results and decisions enabled count when supported. No metric, commercial result or successful deployment is mandatory. After an unknown, declined or skipped question, prioritise stronger evidence or retain appropriately narrow wording; do not invent a learning outcome. Persist reusable new facts in the master evidence and application selection with actual provenance before use.

Professional experience uses reverse chronology between employers and within employers. Ongoing roles come first; completed roles sort by descending end date, with start dates breaking ties. Ongoing ties use the displayed role's original start date, newest first. Preserve overlapping/resumed intervals and supported date precision; do not invent dates or imply consecutive tenure. Manual page breaks must preserve this sequence. Relevance may prioritise bullets within a role. An explicitly requested thematic format is a recorded exception, not an inferred licence to reorder roles.

Independent review checks the strengthening assessment and dispositions against the actual JD/profile/answers, relevance and usefulness of experiment evidence, and source plus rendered chronological order. Skipping a material question without a disposition and a chronology inversion are concrete content/workflow findings, even when individual statements are true.

## Architecture and verification

Author policy under `skills/`, update the agent entrypoint and workflow documentation, and regenerate native host/package copies with `tools/sync_skills.py`. Ordinary private working notes carry assessment evidence; there is no invented record schema. Hooks and Python checks do not prove an interview happened or judge its quality.

The read-only baseline run `/root/interview_chronology_baseline` found that current instructions permit narrow drafting without asking an outcome question and leave chronology discretionary. Revised-policy behavior scenarios will cover strategically weak evidence, sufficient evidence, explicit skips, qualitative/negative outcomes, prior declined answers and interleaved dates. Run the full pytest suite and generated-skill consistency check. No real candidate data belongs in public test fixtures or this design.

## Follow-up: page balance, evidence depth and slow-machine budgets

The required visual review also compares page fill and bottom gaps, not only page count or clean section boundaries. Add a conservative positioned-text `layout_audit` to PDF resume checks, with explicit unavailable states and review signals for unused space before a fuller following page or a sparse final page after a full page. Signals require actual rendered-page review; structural pass and numeric text extents do not establish visual quality. Preserve readable fonts, chronology and meaningful evidence when repairing breaks.

Select from the whole corrected profile for useful JD-relevant depth and breadth within the effective page limit; document important omissions and prefer concrete supported work over thin labels or repetition. A noncritical pending item may be explicitly excluded while other sufficient confirmed evidence supports independent drafting. The unanswered fact must not support claims, eligibility or central fit decisions.

Normal Codex/Claude command hooks receive 120 seconds for constrained local environments; Codex Interrupt retains its documented maximum of three seconds. Preserve existing unrelated local settings and trust decisions. Manual probes test the runner, not native delivery or trust. Tests must cover exported host definitions and the geometry signals using synthetic PDF content; explicitly include the new module in the release allowlist so installation remains standalone.
