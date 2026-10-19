# Review and release status

The review skills are usable instructions for independent host agents. They require precise input files, individual rubric findings, factual entailment, human voice, resume/letter consistency and visual inspection. A host must actually perform these reviews; a name in a JSON fixture is not a reviewer run.

The Python checks validate structure, source joins, job-byte consistency, document text and configured length/page limits. They do not prove that a claim follows from its source, that the full job was extracted or that an independent reviewer inspected the PDF.

Editorial review includes sentence-level meaning as well as paragraph flow:
reviewers check how named employers, teams, products and projects relate in the
actual wording. A user-reported defect reopens the affected verdict even when
the bytes are unchanged. The [fictional editorial scenarios](#cover-letter-editorial-regression-scenarios)
exercise this behaviour without claiming an automated semantic gate.

After any change to evidence, answers, projections, job interpretation, policy, drafts or rendered outputs, the host must repeat affected review. Automatic dependency-complete invalidation is not implemented. The two-round repair limit is a host instruction, not an enforced release gate.

Current rendering produces `unreviewed_preview`; application status is always `draft_only` with `release_available: false`. There is no release/check/copy command. Remaining implementation includes exhaustive typed claim maps, authenticated reviewer runs, complete dependency fingerprints and immutable reviewed-byte release. Manual notes, synthetic acceptance scenarios and successful unit tests cannot authorize production release.

## Cover-letter editorial regression scenarios

These fictional cases exercise the host's sentence-level review. They are not
candidate evidence, an automated language-quality test or release approval.
Give a fresh reviewer the source facts and passages before showing the expected
dispositions. Apply the installed cover-letter review skill. Record actual
findings privately; a successful run does not guarantee future detection.

### Source facts and passages

1. Northbridge Instruments is the employer. Its Imaging team develops the
   FieldLens product. The applicant evaluated image models in an experiment;
   no product deployment is established.

   > At FieldLens, I would join your engineers to compare model accuracy and
   > computational cost. My experimental evaluation work would support that task.

2. Use the same facts.

   > At Northbridge Instruments, I would work with the Imaging team on FieldLens,
   > applying my experimental evaluation experience to model comparisons.

3. The advert names a Boreal initiative but does not establish whether Boreal
   is a company, team or product. The applicant's experience is unchanged.

   > Your Boreal subsidiary would benefit from my experimental evaluation work.

In a follow-up, supply a previous "no findings" report and a user objection to
passage 1. Keep the passage bytes unchanged. Ask which findings can be reused.

### Expected dispositions

- Flag passage 1's employer implication and propose a narrow repair such as
  "Working on FieldLens with the Imaging team, I would compare...". Preserve
  prospective contribution and experimental scope. Explain the relationship,
  rather than only asserting that the paragraph flows.
- Accept passage 2's entity relationships. Do not ban "At" or demand gratuitous
  rewriting of otherwise sound wording.
- Flag passage 3's unsupported subsidiary claim. Use neutral wording about
  contributing to the initiative, or state the unresolved relationship; do not
  invent corporate ownership.
- Reopen the affected editorial verdict after the user objection even without
  a byte change. Clearly scope any reuse of unaffected factual or visual findings.
