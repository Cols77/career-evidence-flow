# Shareability checks

Use a fresh repository with an explicit reviewed file allowlist. Never import the private repository's Git history, profiles, answers, plans, delivered artifacts, secrets or adapters.

Keep the real denylist **outside** this repository. Its format is:

```json
{"rules":[{"id":"private.identity","token":"a privately supplied forbidden value"}]}
```

IDs must be unique and consist of ASCII letters/digits, dots, underscores or hyphens. Tokens must be nonempty. The scanner rejects internal, missing, empty, malformed and duplicate-key denylists. Reports contain relative paths and rule IDs, not matching content.

```powershell
python tools/check_shareable.py --repo . --denylist ../private/denylist.json --mode worktree
git add README.md pyproject.toml src tests tools docs .gitignore
python tools/check_shareable.py --repo . --denylist ../private/denylist.json --mode staged
# Only commit after this passes and the staged file allowlist is reviewed.
python tools/check_shareable.py --repo . --denylist ../private/denylist.json --mode history
```

Staged mode works before the first commit. History mode rejects an empty history and inspects all reachable commit trees, removed historical files, filenames, commit author/committer/messages and annotated/lightweight tag metadata. Worktree mode scans tracked and visible untracked files. Git errors fail closed. Sensitive paths and unexpected binaries block sharing. The scanner accepts source/document formats only; binary output is not part of this distribution.

Tests use synthetic forbidden strings only. A passing denylist scan cannot prove that arbitrary unknown or obfuscated personal information is absent. Review every proposed filename and inspect all copied material manually. Run the staged scan before the first commit, then rerun history and worktree scans against the exact tested revision before any remote push or invitation.

The project is private and unlicensed. GitHub visibility, publication and collaborator access are separate actions after the local privacy report has been reviewed. Do not claim access based on an invitation request; verify pending invitation or accepted write permission explicitly.
