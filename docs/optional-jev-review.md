# Optional JEV evidence-review adapter

`cv_toolkit.jev_review_cli` is an experimental, explicitly invoked external
entailment check. It is not a `cv` subcommand, Hermes hook, automatically invoked
skill step, or release gate. Normal resume and cover-letter workflows do not
require it. It does not replace independent host review, motivation/voice review,
visual inspection or final-resume consistency checks.

## Local, no-network status check

Use the Python interpreter in which the toolkit is installed:

```text
python -m cv_toolkit.jev_review_cli
```

Without `--enable`, this returns `status: disabled`, `advisory: true` and
`route: host_review`, without reading a packet or requesting credentials.
`--enable` without `--allow-external-review` returns `needs_consent` and exit 2.

## Explicit external call (only after consent)

The packet must be a UTF-8 JSON object with exactly five nonempty string fields:
`document` (`resume` or `cover_letter`), `unit_id`, `claim`, `evidence`, and
`snapshot`. Raw input and canonical packet size are bounded to 24,000 bytes.
Keep the packet in the explicit private workspace, not this repository.
The `snapshot` string is supplied context, not an authenticated artifact binding.

Before running, obtain explicit permission both to send the packet's candidate
data to the selected provider and to incur any inference charge. Review and
minimize the packet; possession of a key or an example command is not consent.
The CLI flags record the caller's assertion of consent; they do not authenticate
it or perform an interactive authorization ceremony.

After permission, the invocation shape is:

```text
python -m cv_toolkit.jev_review_cli PRIVATE_PACKET.json --enable --allow-external-review --provider PROVIDER --model MODEL --validated-model EXPECTED_RESOLVED_MODEL
```

Replace placeholders deliberately. Supported provider selectors are `typesafe`
and `openrouter`. Credentials are read from `TYPESAFE_API_KEY` or
`OPENROUTER_API_KEY`, respectively; `--credential-env NAME` selects another
variable name. Never put secret values in the command, packet or version control.
Provider endpoints and response contracts are implemented in
`src/cv_toolkit/jev_review.py`; current external-service compatibility requires
its own authorized live validation, not a fixture test.

## Interpreting results

- Every result is advisory and routes back to host review.
- `ok` means a bounded provider response was parsed, not that the document passed
  review. Inspect `signal`, `probability_supported`, and `version_drift`.
- An absent expected resolved model, or a different returned model, sets
  `version_drift`. The model name returned by the provider is not independently
  authenticated runtime evidence.
- Packet/request hashes bind the submitted payloads, not the truth of evidence,
  reviewer independence or a released PDF.
- Disabled returns exit 0; local consent/input/credential failures return exit 2;
  unavailable/invalid provider responses return exit 3. A valid concern response
  can still return exit 0: success is not factual approval.

No failure should silently become approval. Continue with the independent host
review workflow and report the unavailable or concerning optional signal.
