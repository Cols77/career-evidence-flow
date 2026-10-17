# Reproducible resume visuals

The toolkit packages its renderer, shared layout, themes and fictional demonstration together. No private candidate repository, Google Drive folder or external font service is needed. Keep real resumes in a separate private workspace.

## Compare the designs

After cloning the repository, create a virtual environment and install the toolkit:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[test]"
.venv/Scripts/cv gallery --output outputs/resume-gallery --format both
```

On macOS/Linux, use `python3` and `.venv/bin/python` / `.venv/bin/cv`. PDF generation requires local Chrome/Chromium (or set `CV_CHROME_PATH` to its executable). Use `--format html` to compare without a browser installation. Always use the executable from this toolkit's environment if another project also provides a `cv` command.

Open `outputs/resume-gallery/index.html`. It links to each HTML/PDF, the exact fictional source and `checks.json`. The destination must be new; choose another directory for each revision. A failed render does not publish a partial gallery.

| Visual | CLI style | Character |
| --- | --- | --- |
| Editorial | `branded` | Warm ivory, bronze accents, serif experience headings |
| Modern | `modern` | White paper, navy accents, sans-serif hierarchy |
| Minimal | `minimal` | Black and white, serif typography, fine rules |
| ATS | `ats` | Plain single-column text, stacked dates |

Editorial is the closest to the toolkit's original personal-resume design. The other themes use the same structure and content. HTML adapts to screen width; PDF is the A4 print view. Font fallback and Chromium versions can change line breaks across operating systems, so the layout is reproducible without claiming byte-identical PDFs.

## Work with the fictional resume

```text
cv init ../resume-demo --example showcase
cv validate-evidence --workspace ../resume-demo
cv validate-projection --workspace ../resume-demo
cv render --workspace ../resume-demo --source resume.md --output outputs/editorial.html --style branded
cv render --workspace ../resume-demo --source resume.md --output outputs/modern.pdf --format pdf --style modern
cv check --workspace ../resume-demo --document outputs/modern.pdf
```

The canonical example is `src/cv_toolkit/assets/examples/showcase/`. It includes a substantial resume, fictional evidence, a source registry, projection and configuration. It deliberately remains `synthetic` when inspected with `cv onboard`. Never copy its claims into a real candidate profile. The smaller `developer` and `researcher` examples remain available for application-workflow tests.

## Author the shared layout

Use ordinary Markdown headings: `#` for the candidate, `##` for major sections, `###` for employers or groups, and `####` for roles. Put the role headline and contact line in the first two paragraphs below the name. Include professional links in that same contact paragraph so they sit above the divider, alongside contact information. Use labelled paragraphs for skill and education inventories; start contribution bullets with an action verb and keep each focused on one contribution.

An italic-only paragraph immediately after an h3/h4 becomes its metadata row. Keep dates in this paragraph to align them with the heading in visual themes:

```markdown
## Professional Experience

### Example Employer

*2022–2025*

#### Platform Engineer

- Built a fictional demonstration service.

### Earlier Experience

- Contributed to a demonstration project during an example internship in 2021.

[pagebreak]

## Education
```

Undated h3 groups receive the same visual treatment as employer headings. A standalone top-level `[pagebreak]` paragraph starts a new print page. It does not appear in extracted resume text. Inline code, code fences, blockquotes and ordinary sentences containing that string remain literal. Use the marker sparingly; normal content flows and recurring print margins handle most pagination.

Raw HTML, including a hand-written page-break div, remains rejected. For an older resume that used such a div, replace it in the private source with `[pagebreak]`. The renderer generates its own trusted layout elements. Cover-letter rendering does not apply these resume transformations; `letter` remains the cover-letter style.

## Extend and verify

The shared visual geometry is in `src/cv_toolkit/assets/resume-layout.css`; `branded.css`, `modern.css` and `minimal.css` supply theme choices. `ats.css` remains independent. Assets are loaded through package resources and included in the wheel. Edit the public assets once, then rerender private documents with that installed toolkit.

```text
python -m pytest -q
python tools/sync_skills.py --check
cv gallery --output outputs/resume-gallery-next --format both
```

The gallery checks each HTML/PDF for identity, extraction and page limits, verifies equal content across styles, and compares PDF text with HTML after normalizing case, whitespace, soft hyphens and ligatures. These checks do not prove visual quality: inspect every page for clipping, overflow, orphaned headings and unwanted page breaks. Also inspect HTML at a narrow screen width. The showcase is intended to occupy two A4 pages; a real resume's length depends on its content.

Compare page balance as well as page count. Record content endpoints/bottom gaps and inspect adjacent-page density; an early manual break leaving substantial blank space before a crowded page is a defect to repair or justify specifically. Prefer normal flow and move break positions while preserving chronology and readable text. A clean section boundary alone is insufficient. `cv check` reports conservative PDF text-extent observations in `layout_audit`: review-needed signals require actual image inspection, and an observed audit is not visual approval. Footers, graphics, custom margins and transforms can mislead text geometry; unavailable observations must be disclosed.

Run `tools/verify_installed.py` with a wheel-installed interpreter from outside the source checkout for installation acceptance, including the gallery. Generated PDFs, images and galleries stay in ignored output directories. No test or visual review certifies candidate facts or approves an application for submission.
