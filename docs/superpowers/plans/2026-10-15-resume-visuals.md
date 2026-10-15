# Shared resume visuals implementation plan

> Execution: subagent-driven-development for bounded visual work, test-driven implementation of rendering behavior, and independent review before completion.

**Goal:** Ship reproducible resume designs and a fictional two-page demonstration in the installable toolkit, with no dependency on a private candidate repository.

**Architecture:** Package a shared resume layout plus Editorial (`branded`), Modern (`modern`) and Minimal (`minimal`) themes. Keep `ats` and `letter` available. Convert validated Markdown heading/date pairs and a standalone `[pagebreak]` paragraph into trusted layout markup. Raw HTML and external resources remain rejected. The same source drives every visual option.

**Tech stack:** Python, Python-Markdown, packaged CSS, Chromium PDF rendering, pytest. No remote fonts or rendering services.

## Tasks

- [x] Add failing renderer tests for themes, heading/date flow, undated experience groups, page breaks, unchanged text, and unsafe markup. Implement the shared layout transform and wire CLI style choices to the renderer's supported styles.
- [x] Package the three visual themes with a common layout. Editorial uses warm paper and bronze serif headings; Modern uses navy sans-serif headings; Minimal uses black-and-white serif headings. Keep normal reading order, mobile wrapping and print margins on every page.
- [x] Add a clearly synthetic `showcase` example with fictional resume, identity, evidence, registry and projection. Include dated roles, earlier experience, projects, education and a deliberate page break. Exercise initialization and validation through the CLI.
- [x] Add a repeatable gallery command/script using only packaged assets. Generate HTML/PDF previews and checks for every resume style; ship source and instructions, not personal data or generated binaries.
- [x] Test installation from a built wheel outside the checkout. Run `python -m pytest -q` and `python tools/sync_skills.py --check`. Render every style, check extracted text and pagination, and inspect every page.
- [x] Obtain independent spec, code and visual reviews. Fix material findings. Show a comparison preview and links to the actual PDFs. Record any limitations explicitly.

## Acceptance

A fresh clone can install the toolkit, initialize the showcase and reproduce the gallery without another repository. All visual styles preserve the same content and heading hierarchy. Earlier Experience reads as a group within Professional Experience. The example remains identifiable as synthetic to onboarding and humans. Real candidate data stays outside the repository. Exact line wrapping can vary with installed fonts and Chromium version; no claim of pixel-identical rendering across operating systems.

## Verification performed

- Full suite: 498 passed, 6 skipped. Generated skill copies current; diff whitespace check passed.
- Wheel installed into a separate environment outside the checkout; `tools/verify_installed.py` passed for both original examples, every resume style, cover letters and the four-style showcase gallery.
- Showcase: all four PDFs are two pages, with matching normalized HTML/PDF content and passing document checks.
- All eight showcase pages inspected by an independent visual reviewer; no findings. Independent spec and code reviewers found no actionable issues.
- Chromium screen checks at 1280px and 360px: no horizontal overflow for each resume and the gallery. Used local Chromium because the in-app browser execution tool was unavailable.
- Outputs and review records remain under ignored `outputs/`; no generated binaries or personal candidate content added to the distribution.
