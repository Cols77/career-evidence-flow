# Voice and artifact review

This reference owns the shared editorial criteria for drafting and independent resume/letter review. Apply them within those existing steps and their two-round repair limit; do not create another reviewer, skill, approval stage or detector-scoring loop.

## Private writing preferences

Read `writing-voice.md` in the workspace's configured `[paths].profile` directory, if present. This is an optional agent-maintained working note, not a new CLI record or source of candidate facts. Reuse existing canonical preference records and link to them rather than copying their answers. Record only writing preferences, provenance references and paths to authentic user-supplied samples. Keep all samples and preferences in the explicit private workspace, never in installed skills or public fixtures.

Current user instructions and employer requirements take precedence. Update the note when the user states or corrects a preference, recording the source once through the existing experience-capture process when canonical capture is needed. Distinguish confirmed preferences from suggested defaults. Do not infer a preferred professional voice from casual chat, mistakes, nationality or generated drafts. Without confirmed preferences or a sample, use direct, specific, professional language as a default and proceed; a missing sample is not a blocker. Ask only when the answer materially affects the application.

Include the note, any samples actually used and their referenced preferences in the existing review packet and selected-file checkpoint. A style-input change invalidates the affected voice review through the existing freshness procedure.

## Editorial pass and factual recheck

During drafting, edit once for the intended reader: use concrete supported actions, remove filler and stock enthusiasm, and repair repetitive openings or sentence structures where that improves readability. Match confirmed vocabulary and voice. Retain useful engineering terms, accurate JD keywords, normal resume bullets/headings, deliberate repetition and meaningful punctuation. Do not enforce word blacklists, punctuation bans or artificial sentence-length targets.

Compare the rewrite with the source and support notes before rendering. Preserve numbers, approximate values, dates, uncertainty, negative results, team attribution and prototype/production distinctions. Do not invent opinions, motivation, anecdotes or reactions to add personality. Never introduce errors or weaken clear writing to influence a detector. Repairs use the existing factual review and rerendering process; they do not create a second factual checklist or bypass employer AI-use rules.

Independent reviewers assess the final text against these criteria and the private writing preferences. Report exact passages, the concrete readability problem and a narrow repair, or no findings. A vocabulary pattern is an editorial observation, not proof of AI authorship. No authorship probability or promise of undetectability is warranted. Do not upload candidate documents to detector or rewriting services as part of this workflow.

## Final artifact observations

Run the existing `cv check` on every exact rendered output. Its `artifact_audit` accompanies the ordinary identity, extraction and policy checks for both document kinds. It reports Unicode format-character code points/counts; for readable PDFs, standard metadata field names, counts of other metadata fields and attachments, XMP presence, watermark annotations and page-content non-painting text-mode operators. Metadata values, attachment names and extracted text are omitted from the JSON report.

`observed` means these checks ran. `unavailable` leaves the audit unverified and requires disclosure or repair. An indicator does not automatically fail document checks: renderers commonly write Creator/Producer metadata, and Unicode format characters can be legitimate. Review flagged observations in context. Do not strip metadata, signatures, genuine provenance or characters automatically; do not claim these observations establish authorship or the absence of all watermarks.

The PDF operator check covers page-stream text modes 3 and 7 only. It does not establish actual visibility or inspect form streams, opacity, clipping, white/off-page text or image watermarks. Use the existing independent visual review on every rendered page and compare extracted text with the source; disclose any unavailable inspection. Subsequent edits or metadata changes require renewed checks and reviews on the resulting bytes before export.
