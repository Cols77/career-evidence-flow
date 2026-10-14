---
name: cover-letter-review
description: Use when a cover letter draft or rendered letter needs independent factual, motivation, company-specificity, resume-consistency, voice or visual review.
---

# Cover letter review

Review independently against actual candidate evidence, application answers, employer requirements and the final resume. Read [the review packet](references/review-packet.md) and [the rubric](references/rubric.md).

1. Confirm whether the employer requests a letter and allows the proposed assistance. Obtain the current evidence/registry, actual motivation answers, frozen complete JD, requirement mappings, effective policy, final resume, letter source and exact rendered artifacts. Do not review a prohibited or unrequested letter as a required deliverable.
2. If you authored the letter, use real independent subagents through the host's available delegation tool. Give fresh context and actual files. An already independent reviewer reviews directly. Never substitute imagined personas, scripted fixtures or fabricated runtime identities for independence.
3. Check every paragraph and factual subclaim. Candidate claims need publishable candidate evidence; motivation needs actual answers; company facts need real checked sources or the frozen JD. Preserve prototype/coursework scope, team attribution and limitations. The JD cannot establish applicant experience or enthusiasm.
4. Test role relevance, contribution, company specificity, consistency with the final resume, clarity, human voice and acronym comprehension. A company-swap test may expose a generic letter, but genericness never justifies invented company knowledge. Unknown motivation permits provisional neutral application wording and an explicit gap.
5. Inspect every page of the actual letter with available visual tools. Check typography, spacing, readability, page limits, word limits, clipping, extraction and source/artifact consistency. Run `cv check --workspace ROOT --document PATH --kind cover_letter --policy EFFECTIVE_POLICY_PATH`. Headings and phone are optional unless genuinely required.
6. Return separate factual/consistency, motivation/company, voice/comprehension and visual/artifact verdicts with affected paragraphs/pages, sources, severity and narrow repairs. Record actual reviewer/run evidence and exact inspected revisions. Re-review affected angles after repairs, for at most two rounds.

For Codex continuation, read `cv workflow-status --workspace ROOT --session-id ID` using lifecycle context's actual session ID. Save `cv workflow-checkpoint --workspace ROOT --session-id ID --skill cover-letter-review --phase working` with repeated `--file RELATIVE_PATH` for the complete packet, motivation answers, final resume, letter source and every exact rendered artifact. Snapshot before review; preserve the full selection when deliberately replacing it. Record actual independent agent/tool references, inspected pages and findings in private notes. A child reviewer without its own hook metadata returns findings to the author; never invent a session or overwrite the author's checkpoint using their ID.

Restore from actual records after compaction and respect interruption/current user direction. Run `workflow-status` before final claims/copying outputs: stale final-resume bytes require renewed consistency review; other stale inputs require affected real reviews. `not_recorded` supplies no freshness evidence. `fresh` only covers selected bytes and cannot prove completeness, independence or visual inspection. Compare exported copies to reviewed artifacts; no hook or declaration guards release or authorizes submission.

Missing source, delegation or visual capability leaves those angles unreviewed; keep preview status and explain the precise limitation. Changes to the final resume invalidate letter consistency notes, and changes to evidence, answers or artifacts stale affected reviews.

These are real agent review notes, not authenticated claim maps or production approval records. Automatic freshness enforcement and guarded exact-byte release are unavailable. No skill verdict authorizes submission or overrides employer AI-use policy.
