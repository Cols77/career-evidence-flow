# Codex lifecycle workflows

Codex can load all four installed skills, route a private workspace through the canonical classifier, and restore an explicitly recorded workflow. Hooks supply advisory context; the CLI supplies selected-file SHA-256 comparisons. Neither authenticates reviewer identity, visual inspection, factual truth, or approval. Documents remain previews, with no guarded release.

## Install and activate

Use the installed toolkit environment and an explicit private workspace outside this checkout:

```text
cv init "C:\private\candidate"
cv install-skills --workspace "C:\private\candidate" --host codex
cv install-hooks --workspace "C:\private\candidate" --host codex
```

Omit `init` for an existing workspace. Skills install under `.agents/skills`; hooks install `.codex/hooks.json` and `.codex/hooks/resume-toolkit/`. The standalone bundle contains verbatim classifier/validator modules and a Python isolated-mode runner. It runs offline without this checkout or an importable toolkit package. Its absolute Python executable must remain installed and support Python 3.11+. Moving the workspace or interpreter requires reviewed reinstallation. Config and adapter paths cannot use symlink/junction aliases.

The installer refuses an existing `hooks.json` or adapter directory and preserves them unchanged. For an intentional update or combination, back up and inspect the existing definitions, move the conflicting config/bundle aside yourself, install, then manually merge desired event groups. Preserve private session state separately under `.codex/resume-toolkit/`. Review the final exact hook definitions again.

Start a fresh **local** Codex session in the workspace. Check `codex features list` for hooks availability, inspect `/hooks`, and explicitly trust the toolkit definitions. If your installed host requires enabling hooks, use its documented feature settings. The installer changes no feature setting, project trust, global configuration or hook trust. Confirm all four skills are discoverable and load one linked reference. Hook trust is separate from project/skill trust. Local hooks do not apply to cloud orchestration, even when it can run local commands. See [official hooks documentation](https://learn.chatgpt.com/docs/hooks).

## Lifecycle and scope

| Event | Adapter behavior |
| --- | --- |
| `SessionStart` | Reclassify; restore context for the same session, including resume and compact. |
| `UserPromptSubmit` | Reclassify, restore the declaration and observe new user direction; ignore prompt text. |
| `PreCompact` | Atomically record the event; preserve the existing declaration. |
| `Interrupt` | Record interruption; never restart the turn. |
| `Stop` | Record the event; never block, force continuation or infer completion. |

Restoration uses `SessionStart` with `source: compact`, whose output reaches the next model request. `PostCompact` does not document the additional-context contract used here, so it is not installed. Interrupt output cannot restart work. [Official event contracts](https://learn.chatgpt.com/docs/hooks).

Each invocation checks the host payload's `session_id` and absolute `cwd` against the workspace encoded in its trusted command and installed location. Child directories are allowed, but an intervening nested `cvtool.toml` workspace is rejected. Other workspaces, missing/invalid session IDs and unsupported events are silent. Process cwd and message/transcript content never select the workspace. Hooks are local advisory code, not an authentication mechanism or security sandbox.

Checkpoint state stores enums, session/workspace digests and explicitly selected relative file paths/hashes. Execution diagnostics described below also store timing, process and adapter metadata. No prompt, transcript, candidate identifier, claim text, answer or assistant response is stored. Filenames in snapshots can themselves be private; keep the state private. New workspaces ignore `.codex/` in Git; add an appropriate ignore rule yourself for an older workspace. Input is limited to 256 KB, snapshots to 64 files of at most 128 MB each. Failures return a generic warning without private exception text. An exclusive session lock prevents lost writes; atomic replacement prevents partial JSON.

## Execution logs

The installed runner automatically writes one JSON file per invocation under
`.codex/resume-toolkit/logs/`. It writes `stage: started` before reading stdin,
then atomically updates the same record to `stage: completed`. A record that
remains started indicates incomplete observation, such as a killed or hung
process; it does not establish why the process stopped.

Records contain UTC start/end times, elapsed milliseconds, process and invocation
IDs, session/workspace SHA-256 digests, the `codex_hooks.py` digest, allowlisted
event/source names, route/freshness when evaluated, and an outcome:
`context_emitted`, `observed`, `ignored`, `error`, `invalid_input`, or
`workspace_mismatch`. Successful `Stop` observation is not workflow completion.
Unique files avoid concurrent append collisions. Logs accumulate locally until
the owner removes them; no background upload or automatic deletion occurs.
Logging failures emit a generic stderr warning and leave routing operational.

For a direct runner test, append `--probe` to label the record `manual_probe`.
Installed hook commands use `hook_command`. Neither label authenticates the
caller: a manual call without `--probe` also looks like a hook command. Every
record therefore has `native_origin_verified: false`. To establish native
delivery, correlate the time, event and SHA-256 of the host session ID with
Codex's own hook-start/completion events. An empty log folder alone cannot
distinguish an untrusted/skipped hook from a launch or logging failure.

PowerShell inspection from the private workspace:

```powershell
Get-ChildItem .codex/resume-toolkit/logs/*.json |
  Sort-Object LastWriteTime |
  ForEach-Object { Get-Content -Raw -LiteralPath $_.FullName | ConvertFrom-Json } |
  Select-Object started_at, event, stage, outcome, mode, duration_ms
```

## Record and resume

Lifecycle context supplies the validated session ID for these commands. Do not invent one from filenames, another conversation or global environment. Without that metadata, use canonical private records manually and report automatic restoration as unavailable.

```text
cv workflow-checkpoint --workspace "C:\private\candidate" --session-id SESSION_ID --skill experience-capture --phase waiting_for_user
cv workflow-status --workspace "C:\private\candidate" --session-id SESSION_ID
```

Skills are `experience-capture`, `application-materials`, `resume-review`, `cover-letter-review`. Phases are `working`, `waiting_for_user`, `blocked`, `paused`, `finished`. All phases are declarations, including `finished`; none proves completion. The saved skill guides authorized continuation when canonical prerequisites permit it. Current user direction takes precedence. Waiting/paused/blocked work does not resume automatically. Compaction and resuming the same session retain its checkpoint. A genuinely new session ID starts empty.

For a new conversation, explicitly inspect the previous session with `workflow-status --session-id OLD_ID`, reconcile its records against the current request and canonical files, then record an appropriate checkpoint with the **new** hook-supplied ID. This is a deliberate host action, not automatic state copying. Child reviewers without their own hook metadata return findings to the author; they must not overwrite the author's checkpoint using its session ID.

Save actual answers once using the existing provenance workflow. Checkpoints never replace evidence, answers, applications or actual reviewer notes. `PreCompact` preserves only already recorded metadata, not unsaved thoughts or edits.

## Exact files and review

Before real independent reviewers start, snapshot all selected inputs and outputs. For example:

```text
cv workflow-checkpoint --workspace ROOT --session-id SESSION_ID --skill resume-review --phase working --file cvtool.toml --file profile/evidence.json --file profile/registry.json --file profile/projection.json --file applications/ROLE/application.json --file applications/ROLE/job.txt --file applications/ROLE/requirements.json --file applications/ROLE/questions.json --file applications/ROLE/effective-policy.json --file applications/ROLE/resume.md --file outputs/ROLE/r01/resume-ats.pdf --file outputs/ROLE/r01/resume-branded.pdf
cv workflow-status --workspace ROOT --session-id SESSION_ID
```

Use actual configured paths and actual packet files, including relevant style inputs. For a letter, also select motivation answers, final resume, letter source and exact rendered letter. Every checkpoint command **replaces the full previous selection**, even when no `--file` is supplied. Run status before replacing a snapshot so replacing it cannot conceal staleness from your review process.

`fresh` means selected files still have recorded bytes. `stale` identifies changed/missing selected files: repair, rerender and redo affected real reviews before recording a replacement. `not_recorded` means no file fingerprints exist. `status: ok`/exit 0 means the query ran successfully, not that freshness passed. Output always includes `review_status: unreviewed_preview` and `release_available: false`.

The host must select a complete packet, dispatch actual independent agents, preserve real tool/run references in private notes, and inspect every requested rendered page with available visual tools. A typed reviewer ID or hash cannot prove these actions occurred. Missing delegation or visual capability remains an explicit limitation. Check snapshots immediately before final claims or authorized export/copying. Compare destination hashes with the reviewed source artifacts (for example, PowerShell `Get-FileHash -Algorithm SHA256` on both). No guarded export command exists; later edits can invalidate observations and no snapshot authorizes submission.

## Diagnose and prove delivery

1. Run `cv onboard --workspace ROOT` and `cv workflow-status --workspace ROOT --session-id SESSION_ID`. An empty session returns `not_recorded`; malformed/cross-bound state fails validation. Repair from canonical records, not invented checkpoint contents.
2. Confirm the interpreter/adapter paths in `hooks.json` exist. Inspect `/hooks` for failed, disabled or untrusted definitions. Restart after installing or changing definitions.
3. In a disposable synthetic workspace, ask the agent to report its injected toolkit route/session ID without editing evidence. Run `workflow-status` for that ID and verify the observed event/route. Invoke `/compact`, then ask for the restored declaration; inspect actual host hook logs/context where available. A model repeating a requested phrase alone does not prove delivery. Record host/version and real tool outcomes privately.
4. For a busy checkpoint, stop competing writers and inspect `.codex/resume-toolkit/sessions/SESSION_DIGEST.lock`. Remove only a confirmed abandoned lock after no writer is active. Never blindly delete session state to clear a warning.

Automated tests exercise synthetic stdin contracts, canonical routing, isolation, interruption, malformed records, freshness, Windows quoting, junction rejection, no overwrite and standalone installed bundle invocation. A fresh wheel is separately exercised outside the checkout. These checks **do not prove native skill discovery, trusted hook delivery in a live chat, compaction UI behavior, actual independent reviews or visual inspection**. Native acceptance requires the activation/probe above. Package tests do not require a paid/model session or trust bypass. Hermes keeps its separate adapter; Claude hook installation remains unsupported.
