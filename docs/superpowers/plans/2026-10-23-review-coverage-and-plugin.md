# Review coverage ledger, Claude Code reviewer workflow and plugin packaging

Intent: INT-004 (review coverage), INT-006 (plugin), INT-001 (plumb adoption), INT-007 (lazy).
Existing behaviour (INT-002, INT-003, INT-005) is already proven by the test files its
requirements name; nothing in it changes.

## 1. Review ledger (SR-009, SR-010)

Add `record_review` and `review_status` to `src/cv_toolkit/application_tools.py`, next to
`verify_bundle`, reusing `confined`, `load_json`, `atomic_write_json` and the bundle digest.

- Angles: resume `factual, alignment, voice, visual`; cover_letter
  `factual, persuasiveness, motivation, voice, visual`. Verdicts `pass, findings, unavailable`.
- `reviews.json` beside `bundle.json`: `{schema_version: 1, reviews: [...]}`, append-only.
  Each entry stores document, angle, verdict, bundle SHA-256, the SHA-256 of that document's
  rendered artifacts, recorded-at, optional findings path (under outputs) and reviewer text.
- `review_status` uses the policy deliverables in the bundle context; the latest entry per
  angle wins; states `recorded`, `missing`, `stale` (artifact hashes differ), `unavailable`.
  Always `review_status: unreviewed_preview`, `release_available: false`.
- CLI: `cv record-review` and `cv review-status`, both taking `--bundle`.

Tests, one per example, in `tests/test_review_ledger.py` with the HTML-only bundle fixture
pattern of `tests/test_application_tools.py`:
1. a pass verdict is stored with the current resume artifact hashes;
2. a findings verdict without a findings file is refused;
3. a resume verdict naming `persuasiveness` is refused;
4. resume angles recorded and letter angles missing are reported as such;
5. a rebuilt (changed) resume artifact turns its verdict stale;
6. a resume-only policy requires no letter angle.

## 2. Claude Code reviewer workflow and skill text (SR-011)

- `.claude/workflows/review-angles.js`: a saved Workflow script taking `{workspace, bundle}`;
  it runs `cv review-status`, spawns one reviewer agent per missing or stale angle in
  parallel with the review packet path and a verdict schema, then records each result with
  `cv record-review`.
- `skills/application-materials/SKILL.md` step 7, `skills/resume-review/SKILL.md`,
  `skills/cover-letter-review/SKILL.md`: record each angle's verdict with `cv record-review`,
  run `cv review-status` before returning previews and name every angle not recorded. On
  Claude Code, run the saved `review-angles` workflow; on other hosts dispatch one reviewer per
  angle. Then `python tools/sync_skills.py`.
- `docs/review-and-release.md`: a short section on host coverage (Codex and Hermes rely on the
  skill instruction; review-status shows their gaps).

## 3. Plugin (SR-013)

- `.claude-plugin/plugin.json` at the repository root: name `resume-toolkit`, version from
  `pyproject.toml`, description, author, keywords. Skills are discovered from `skills/`.
- README: how to load it with `claude --plugin-dir`.
- `tests/test_package.py`: the manifest names the plugin and every canonical skill folder has a
  SKILL.md with name and description frontmatter.
- `claude plugin validate .` passes.

## 4. Plumb adoption (INT-001)

Commit `.plumb/` records and the test map with the code. Relink SR-009 and SR-010 to
`application_tools.py`, SR-011 to the workflow file, SR-013 to the manifest once they exist.

## Proof (agreed with the owner)

A live Claude Code session started with `--plugin-dir` on this checkout, on the fictional
showcase profile in a scratch workspace: the five skills are listed, a revision is built,
the workflow dispatches one reviewer per angle, and `cv review-status` shows every angle
recorded.
