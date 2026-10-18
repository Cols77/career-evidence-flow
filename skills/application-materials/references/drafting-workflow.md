# Host drafting and review workflow

## Inputs and working files

Read workspace identity/contact choices, canonical evidence and registry, application projection, frozen complete JD, requirement mappings, actual question answers and effective employer policy. Resolve real contradictions before publication. Skills work with existing `cv` commands; `cv --help` and each command's `--help` are authoritative for syntax.

Draft in application-specific source paths recorded in `application.json`, normally `applications/SLUG/resume.md` and `applications/SLUG/cover-letter.md`. Preserve historical/final originals and other applications. Use revision-specific outputs such as `outputs/SLUG/r01`. Ordinary authorized draft edits and repairs do not require repeated approval.

Put every generated PDF, HTML, page image and extracted-text file beneath the workspace's configured `[paths].outputs` directory. `cv init` creates `outputs/` and a matching `.gitignore` rule. For an existing workspace or custom output path, ensure that directory's contents are ignored before rendering; use `git check-ignore` when the workspace is in Git and check that generated files are not already tracked. Keep editable application sources separate from generated outputs. The bound Git-ignored `user-profile/` child workspace is supported; never place real candidate files in tracked/public toolkit paths.

## Focused evidence strengthening before drafting

Before a new draft or substantive tailoring, compare the complete JD's most important needs with the current profile and actual prior answers. Do this even when every old bullet is technically true: factual sufficiency does not establish that the strongest relevant evidence has been elicited. This is a required assessment inside drafting, not a separate exhaustive interview or approval ceremony. Pure formatting changes and mechanical corrections do not reopen it.

Identify the few opportunities most likely to change evidence selection, specificity, credibility or fit. Read the actual experience before choosing questions. A useful question targets a concrete missing detail, such as who used a relevant tool, what was personally delivered, how a result was evaluated, what an experiment established, or what decision it enabled. Do not recite every JD keyword, ask a standard questionnaire, repeat answered/declined questions, or insert an item simply because its tool name matches the advert. Existing gaps deliberately resolved as unknown or declined are not automatic new interview opportunities.

Ask at most three focused questions per exchange, prioritised by likely value. For example, when retrieval quality is central to a role and the profile only records a retrieval experiment, ask what problem it addressed, how answers were checked, and what worked, failed or changed as a result. Do not ask for a productivity percentage by default. A qualitative learning, negative finding, limitation or design decision is useful when the candidate actually supplies it; never invent one to strengthen a weak bullet.

Record a short assessment in ordinary private working notes under the configured output directory: the key JD need, relevant evidence/answer references, missing detail, why it matters, and question/disposition. If the profile already answers the useful questions, record that conclusion with references and proceed without a token question. There is no fixed template or new CLI schema. Include the notes and actual referenced answers in the independent-review packet and freshness selection.

When a material unanswered opportunity is identified, ask and wait before drafting claims or making eligibility/core-fit decisions that depend on it. A request to regenerate quickly, an empty question file, or the option to write narrower wording does not waive this step. Continue independent preparation while waiting. Explicit permission to skip/proceed with existing evidence, an actual unknown/declined answer, or a previously resolved gap permits honest drafting after recording the disposition; silence and elapsed time do not. The noncritical-item deferral below permits independent supported drafting, not use of the missing answer. In an unattended run without a permissible disposition, report the pending interview instead of silently declaring it complete.

An outstanding question must remain explicitly pending. If its item can be excluded without guessing about eligibility or a central fit decision, defer that item and draft from other sufficient confirmed evidence; record the exclusion and pending question for review. This is not a fabricated answer, an implicit waiver or permission to use the missing result. Do not block unrelated mechanical repairs or supported work on an answer they do not depend on.

Capture actual answers once with provenance using experience-capture. Add reusable experience to canonical master evidence, then update application selections and support notes before using it. Preserve uncertainty and project maturity. If no meaningful outcome or learning is established after this step, prioritise stronger evidence or retain narrow experiment wording where it still adds value; do not demand success, metrics or commercial impact as a condition of inclusion. The host follows this policy; existing hooks and preview commands do not mechanically enforce it.

## Resume

Choose sections and ordering for the role and the person's actual background. Do not force training, awards or a summary when they add no supported value. Use actual supplied identity/contact facts, dates, degrees and availability. The default workspace name is not verified identity.

Read the full canonical master and actual correction sources before selecting evidence; the previous resume/projection is not the whole profile. Within the effective two-page limit (when applicable), aim for the greatest useful JD-relevant depth and breadth: demonstrate concrete methods, ownership, evaluation, delivery and results across the strongest relevant capabilities. Compare the value of additional supported evidence with repetitive/generic text already selected. Preserve distinguishing contributions rather than prematurely shortening to fit an arbitrary section boundary. Record important omissions and their relevance/space rationale for reviewers. Do not include every stored item, add filler, invent impact or shrink text to gain nominal coverage. Prefer strong supported contributions over thin experiment labels; a pending strengthening question can justify deferring that item.

Keep professional experience in reverse chronological order both between employers and among roles/assignments within an employer. Ongoing roles precede completed roles; completed roles sort by most recent end date, then most recent start date. For ongoing roles with equal end status, use the most recent original role start date first. Preserve supported date precision, explicitly overlapping streams and resumed intervals; do not infer ongoing employment from a missing end date, invent dates or add overlapping tenures together. Raise material missing/ambiguous dates rather than silently guessing. An older completed role must not precede newer experience simply because it fits the JD better.

Manual page breaks, continued-employer headings and an Earlier Experience group must preserve this sequence. Relevant bullets within a role may be prioritised by the JD; they need not be chronological. Do not invent dates for undated projects or turn skills/projects into a fictitious employment timeline. An explicitly requested thematic format is an exception to record and review, never an exception inferred from relevance. Check the source and final rendered reading order.

For each summary, skill and bullet, record a working support note with source unit, factual subclaims, evidence IDs, ownership, maturity and limitations. This is an agent-authored workpaper, not an authenticated toolkit claim map. Existing `resume_claims`/`cover_letter_claims` manifest paths reserve future functionality; do not fill them with an invented production schema.

Select truthful actions and supported context/outcomes. A local prototype is not a production deployment. A team result is not personal sole ownership. Approximate values remain approximate. Coursework demonstrates coursework, not commercial experience. Mention tools only where evidence establishes their actual use. A listed skill needs evidence and visible same-document proof; otherwise omit it or record a specific unresolved finding. Do not invent an exception approval.

Use JD keywords only when their meaning matches the candidate's actual experience. Explain acronyms on first relevant use and ensure the owner understands the terminology. Apply the shared [voice and artifact review](voice-and-artifacts.md): load private writing preferences, edit for clarity and recheck factual scope before rendering. These criteria also apply to the cover letter.

Apply its action-led, one-contribution-per-bullet review to every resume bullet. Keep labelled skill and education inventories outside bullet lists. Put professional links in the same contact paragraph as the location, phone and email, above the header divider; let the row wrap naturally on small screens and inspect the final PDF for spacing.

## Cover letter

Before writing, record a brief hiring argument in private working notes: the employer's main need, the supported contribution this candidate can make, and the one or two best examples with their evidence references. Explain why these examples earn space over other resume content. This is a drafting aid, not a new record schema or a claim that future impact is proven.

Assess motivation deliberately using existing answers: record the genuine reason and its source, or the unknown/declined disposition. Ask one focused unanswered question only if it could materially strengthen this letter; do not ask again when a useful answer or explicit decline is already recorded. Follow the strengthening assessment's wait/deferral rules for material questions. Unknown motivation permits a provisional neutral opening stating the application purpose and supported contribution, with the gap visible in notes. Never infer enthusiasm from the JD or fabricate admiration, a long-standing passion or company familiarity. A no-letter employer instruction removes the letter deliverable and its motivation question. A prohibited AI-use rule prevents AI-generated application material, even though renderer commands would technically run.

Use the final resume, actual answers and sourced company facts to develop the argument. Company facts require the frozen JD or an actual checked source. Give each paragraph a distinct purpose: establish relevant interest or contribution, demonstrate it through selected evidence, or explain its relevance to the employer's problem. Connect one or two experiences to concrete needs rather than retelling the resume. Explain what a supported result, learning or decision demonstrates without inventing business impact. Technical details earn space when they explain the contribution; remove tool inventories, repeated delivery details and generic closing claims that do not advance the argument. Preserve necessary ownership and maturity boundaries without repeating them in every paragraph. Do not force an arbitrary word target below the employer limit or omit useful evidence merely for brevity.

Run the explicit [cover-letter fluency pass](voice-and-artifacts.md#cover-letter-fluency-pass) after substantive drafting and before rendering: check the connection between adjacent ideas, transitions, sentence rhythm and uninterrupted natural reading. Repair missing links in the argument rather than adding stock connecting phrases. Record meaningful repairs or why no useful change remains in the existing notes.

Recheck factual support, persuasiveness and fluency after editing. A fully supported letter can still fail to explain why this candidate fits this role or move awkwardly between ideas. Include the brief argument, motivation assessment and fluency observations in the review packet, but have the independent reviewer first read the letter and JD before the author's rationale so that the argument and flow must stand on their own.

## Rendering and checks

Use installed commands instead of application-specific Python scripts. The host
authors requirements, selects evidence and writes Markdown; reusable tools handle
the mechanical preparation, rendering, checking and fingerprinting:

```text
cv application-context --workspace ROOT --application applications/SLUG
cv build-application --workspace ROOT --application applications/SLUG --output outputs/SLUG/r01 --include outputs/SLUG/strengthening-assessment.md --include outputs/SLUG/support-notes.md --include profile/sources/actual-answer.json --page-images
cv verify-bundle --workspace ROOT --bundle outputs/SLUG/r01/bundle.json
```

Use actual `--include` paths, repeated for every source document, prior answer,
master narrative, writing preference and support note consulted. The paths above
are examples. Standard profile/application records, selected extras, packaged
styles, skills and renderer/checker code are fingerprinted. Input files are copied
into the bundle. The command cannot discover all semantic dependencies: inspect
the selection and disclose unavailable sources. Registry declarations alone do
not establish source-byte freshness.

The build uses the manifest policy and defaults to ATS/branded HTML and PDF resumes
and a letter only when included in the deliverables. Repeat `--style` to select
other resume variants. `--format html` works without Chromium but cannot establish
PDF pagination. `--page-images` rasterizes every PDF page and requires the optional
`visual` extra (`pip install "resume-toolkit[visual]"`); omit it and disclose missing
visual tooling when unavailable. Generated images still need actual inspection.

Each build requires a new directory under configured outputs and verifies Git
ignore rules in repositories. Standalone non-Git workspaces require a literal
output ignore rule and report Git enforcement as unverified. Incomplete extraction,
pending material questions, missing files and forbidden/restricted AI policy block
the convenience command. Never change truthful policy/question records simply to
make it run. For restricted policies, assess actual restrictions with the host;
individual mechanical commands may be used only when permitted.

Check failures retain a diagnostic bundle and return a nonzero status. Operational
failures publish no partial revision. Inspect `checks.json`, `review-packet.md`,
frozen `inputs/` and every artifact page. Keep review notes outside the immutable
revision and build a new revision after repairs. `verify-bundle` checks selected
bytes before review and handoff; it does not authenticate the editable manifest,
establish semantic completeness, authenticate reviewers or enforce release.

Individual commands below remain available for targeted diagnosis.

Save the complete effective policy as `applications/SLUG/effective-policy.json`; preserve the matching manifest policy. Example commands use existing functionality:

```text
cv render --workspace ROOT --source applications/SLUG/resume.md --output outputs/SLUG/r01/resume-ats.html --style ats
cv render --workspace ROOT --source applications/SLUG/resume.md --output outputs/SLUG/r01/resume-branded.html --style branded
cv render --workspace ROOT --source applications/SLUG/cover-letter.md --output outputs/SLUG/r01/cover-letter.html --style letter --kind cover_letter
cv check --workspace ROOT --document outputs/SLUG/r01/resume-ats.html --policy applications/SLUG/effective-policy.json
cv check --workspace ROOT --document outputs/SLUG/r01/cover-letter.html --kind cover_letter --policy applications/SLUG/effective-policy.json
```

For PDF use the same source with a `.pdf` output and `--format pdf`. Chromium/Chrome is required. PDF generation regenerates HTML from current Markdown; it does not authenticate reviews or certify visual quality. Raw HTML, embedded images and active/resource markup are rejected. Keep links ordinary HTTP(S), mailto or fragments.

Resume visuals are packaged with the toolkit: `branded` (warm editorial), `modern` (navy sans-serif), `minimal` (monochrome serif), and `ats` (plain). Select the style within the employer's format constraints and the user's preferences. An italic-only paragraph immediately below an h3/h4 is its date/metadata row; an undated h3 such as Earlier Experience keeps the same group hierarchy. A standalone top-level `[pagebreak]` paragraph requests a print page break without raw HTML. For visual development, use `cv init ROOT --example showcase` or `cv gallery --output NEW_DIRECTORY --format both`; the packaged example is fictional and never evidence about the candidate.

HTML checks cannot establish final PDF pagination. If PDF or visual tooling is unavailable, explain which check was not exercised and retain preview status. Do not fabricate screenshots or label an unobserved artifact visually reviewed.

### Page balance and usable space

Treat avoidable large blank areas as layout defects, even when the PDF fits the page limit. Compare all pages side by side and record each page's content end/bottom gap and its next or previous page's density. Normal margins and some final-page space are expected; a forced break leaving room for a heading and substantive content while the following page is crowded requires a repair or a specific, evidenced justification. A clean employer boundary, deliberate break or two-page count alone is not a justification.

Start with normal flow. Remove or reposition early manual breaks, allow roles to continue across pages with clear context, and rerender both requested styles. Preserve chronology, readable type, heading association, complete bullets and all selected evidence while adjusting pagination. Do not hide the gap by adding filler, shrinking fonts, changing dates or dropping valuable evidence. Review both directions: an overfull first page followed by a nearly empty final page is also a distribution concern.

`cv check` includes a PDF `layout_audit` using positioned text extents and a 14 mm reference margin. `review_needed` flags substantial unused space before a fuller next page or a sparse final page after a full page. These are conservative review signals, not painted-area measurements or automatic rejection: footers, images, clipping, nonstandard margins/transforms and rotation can mislead or make the audit unavailable. A structural `pass` does not resolve the layout findings. Inspect the exact images and document repair or a concrete false-positive explanation before returning a visual no-findings verdict. For HTML or unavailable geometry, do the same check with actual PDF/page images when possible and disclose missing tools.

Review `artifact_audit` from the same `cv check` result as described in [voice and artifact review](voice-and-artifacts.md#final-artifact-observations); no separate audit command or detector service is needed.

## Independent review and finish

Use `resume-review` and `cover-letter-review`. Delegate to actual independent subagents through the host's available delegation tool, using fresh context and the real packet. One reviewer may cover several angles only with separate findings and verdicts. A self-check, fixture, simulated response or manually typed reviewer ID does not establish independence.

Apply supported repairs, update working support notes, render a new revision and rerun affected reviewers/checks. Changes to facts, answers, JD, policy, text, styles or artifacts invalidate related review notes; the host tracks this manually. Stop after two review/repair rounds and report remaining findings.

Return requested artifacts and a short account of evidence gaps, actual reviews, visual capabilities and remaining findings. Existing commands always yield previews. Authenticated claim maps, enforced review freshness and guarded exact-byte release are unavailable; independent review notes do not create submission authorization.
