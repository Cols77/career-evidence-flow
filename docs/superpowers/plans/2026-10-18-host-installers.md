# One-command host installers

User chose repository installers for Codex, Claude Code and Hermes. Keep one
cross-platform `install.py` with host arguments, backed by one installed command:
`cv install-agent`. Python 3.11+ and an existing configured agent are prerequisites.

The bootstrap creates a shared per-project environment under ignored `.local/`,
installs this checkout, and invokes the selected host integration. `--hooks` opts
into advisory hook files; host trust and native activation stay explicit. A
managed environment marker permits recovery and reuse, never commandeering an
unrelated environment. No shell interpolation or downloaded script execution.

Keep current `setup`/`install-hooks` behavior conservative. Refactor hook payload
construction into shared pure functions. The new installer preflights desired
skills/hook bytes against current files and an ignored, versioned ownership
inventory. Accept exact current package bytes or unchanged previously recorded
bytes. Refuse custom, missing, unexpected or aliased integration files. Existing
owner instructions and canonical profile/application data are preserved.

For shared host JSON, record only owned hook groups. On upgrade, require those
groups exactly once and unchanged, replace only them, and preserve all other
current settings/groups. Never recreate settings from an old baseline. Reinstall
refreshes previously managed hooks without enabling previously absent hooks.

Plan every write before applying it, recheck originals, save private backups and
roll back managed-file writes on failure. Record inventories last. Validate every
inventory path against known integration destinations; inventory is local
ownership metadata, not authenticated review or authorization.

Tests: initial installation for each host, unchanged repeat, managed package
upgrade, profile/instruction preservation, custom file refusal, shared settings
preservation, managed group edits, aliases/path escapes, recovery after failure,
and sequential host installation sharing one environment. Verify actual bootstrap
and installed CLI using fictional workspaces, then full pytest and skill-sync
checks, independent review, privacy scan and push main. No real applications.
