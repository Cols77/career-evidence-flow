# Contributing

Start from [AGENTS.md](AGENTS.md). Product work should keep the agent-led application flow and the deterministic helpers aligned. Real candidate facts belong in an explicit private workspace; examples and tests use synthetic data.

Install `.[test]` in a virtual environment and run `python -m pytest -q`. For skill changes, edit only `skills/`, run `python tools/sync_skills.py`, then `python tools/sync_skills.py --check`. Generated native-host and wheel copies must match the canonical source, including reference files. Run a synthetic agent scenario for changed interview, drafting or review behavior; unit tests alone cannot prove a skill works for an agent.

Build a wheel and exercise its installed skills from outside the checkout when distribution changes. `tools/verify_installed.py` validates both synthetic profiles, host file installation and local document previews; PDF checks require Chrome/Chromium. This does not demonstrate native host discovery or guarded release.

Before sharing, follow [privacy checks](docs/privacy.md), using an external private denylist and a reviewed file allowlist. Do not commit private profiles, host state, credentials, local verification notes or generated candidate outputs. The project currently has no open-source license.
