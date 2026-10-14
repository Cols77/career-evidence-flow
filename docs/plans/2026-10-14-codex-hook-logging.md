# Codex hook execution logging

The user requested execution logs as concrete runtime evidence. Add diagnostics to
the installed runner, retaining its existing routing and output contract.

Each invocation writes a unique private JSON record before reading stdin, then
atomically replaces it on completion. This avoids shared-log write collisions
and leaves a started record if the process is killed. Record UTC timestamps,
duration, process ID, event/source enums, session/workspace digests, adapter code
digest, route/freshness and outcome. Never record prompts, responses, transcripts,
candidate content, file paths or exception text. Logging errors warn generically
on stderr and cannot break routing. Records are local diagnostics, not approvals.

Use `--probe` to label explicit manual calls. The default hook-command label does
not authenticate native origin: corroborate it with the host's hook events and
session digest. Do not invent a native success from a synthetic stdin call.

Implementation and verification:

1. Add installed-runner tests and observe their failure before implementation.
2. Add minimal logging, including success, ignored input and failure outcomes.
3. Test privacy, independent records, aliases, logging failure and killed runs.
4. Document the log location and native/manual evidence distinction.
5. Run the full suite and skill sync check; independently review the change.
6. Back up and update the user's installed adapter without changing trust settings.
7. Exercise labelled probes and inspect available native host discovery/events.

Atomic per-invocation files were chosen over shared JSONL/rotation to keep writes
independent and preserve failed/incomplete runs. No central service or release
gate is introduced. Logs accumulate until the workspace owner removes them.
