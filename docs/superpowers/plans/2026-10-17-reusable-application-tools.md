# Reusable application tools

The host remains responsible for interviews, evidence selection, prose and actual
independent review. Replace per-application rendering and fingerprint scripts with
installed CLI commands usable by Codex, Claude Code and Hermes.

1. Add `application-context`: validate the canonical profile/application and return
   explicit input paths, policy, pending questions and requirement gaps. No drafts.
2. Add `build-application`: render policy-selected deliverables from existing
   Markdown into a new revision under configured outputs; run existing checks;
   optionally rasterize PDFs; save checks, source copies and a dependency manifest.
   Default resume styles are ATS and branded. Never overwrite an existing revision.
3. Add `verify-bundle`: recompute recorded workspace, package and artifact hashes;
   report changed/missing dependencies and preserve unreviewed preview status.
   Explicit extra files cover prior answers, source documents and support notes;
   the command cannot prove semantic completeness or reviewer independence.
4. Test with fictional profiles, including failures, policy restrictions, path
   confinement, output ignores, stale sources and packaged CLI execution.
5. Update canonical skills and sync all distributed copies. Run the full suite,
   release/install verification, independent code review and private denylist scan.
   Commit only intended public files and push reviewed changes to main.
