# Review and release status

The review skills are usable instructions for independent host agents. They require precise input files, individual rubric findings, factual entailment, human voice, resume/letter consistency and visual inspection. A host must actually perform these reviews; a name in a JSON fixture is not a reviewer run.

The Python checks validate structure, source joins, job-byte consistency, document text and configured length/page limits. They do not prove that a claim follows from its source, that the full job was extracted or that an independent reviewer inspected the PDF.

After any change to evidence, answers, projections, job interpretation, policy, drafts or rendered outputs, the host must repeat affected review. Automatic dependency-complete invalidation is not implemented. The two-round repair limit is a host instruction, not an enforced release gate.

Current rendering produces `unreviewed_preview`; application status is always `draft_only` with `release_available: false`. There is no release/check/copy command. Remaining implementation includes exhaustive typed claim maps, authenticated reviewer runs, complete dependency fingerprints and immutable reviewed-byte release. Manual notes, synthetic acceptance scenarios and successful unit tests cannot authorize production release.
