"""Installed skills must retain their executable workflow references."""
from pathlib import Path

import pytest

from cv_toolkit.bootstrap import SKILLS, install_skills
from cv_toolkit.records import ToolkitError


@pytest.mark.parametrize('host,prefix', [
    ('codex', '.agents/skills'), ('claude', '.claude/skills'), ('hermes', '.hermes/skills'),
])
def test_installer_preserves_nested_resources(tmp_path, monkeypatch, host, prefix):
    # A resource-only fixture detects installers that silently drop references.
    package = tmp_path / 'package'
    for name in SKILLS:
        folder = package / 'assets' / 'skills' / name
        (folder / 'references' / 'nested').mkdir(parents=True)
        (folder / 'SKILL.md').write_text('[Read](references/nested/workflow.md)', encoding='utf-8')
        (folder / 'references' / 'nested' / 'workflow.md').write_bytes(b'workflow reference\n')
    monkeypatch.setattr('cv_toolkit.bootstrap.files', lambda _: package)
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    assert install_skills(workspace, host) == len(SKILLS)
    for name in SKILLS:
        assert (workspace / prefix / name / 'references/nested/workflow.md').read_bytes() == b'workflow reference\n'


def test_existing_reference_blocks_entire_install_without_writes(tmp_path):
    preserved = tmp_path / '.agents/skills' / SKILLS[-1] / 'references/owner.md'
    preserved.parent.mkdir(parents=True)
    preserved.write_bytes(b'owner instructions')
    with pytest.raises(ToolkitError):
        install_skills(tmp_path, 'codex')
    assert preserved.read_bytes() == b'owner instructions'
    assert not (tmp_path / '.agents/skills' / SKILLS[0]).exists()


def test_packaged_skill_links_resolve_after_install(tmp_path):
    import re
    install_skills(tmp_path, 'codex')
    for name in SKILLS:
        folder = tmp_path / '.agents/skills' / name
        markdown = list(folder.rglob('*.md'))
        assert len(markdown) >= 2, f'{name} needs supporting workflow instructions'
        for page in markdown:
            for link in re.findall(r'\]\(([^)]+)\)', page.read_text(encoding='utf-8')):
                if '://' in link or link.startswith('#'):
                    continue
                target = (page.parent / link.split('#')[0]).resolve()
                assert target.is_relative_to(tmp_path), f'escaping skill reference: {link}'
                assert target.is_file(), f'broken installed reference: {link}'


def test_repository_and_wheel_skill_copies_are_current():
    root = Path(__file__).resolve().parents[1]
    for name in SKILLS:
        canonical = root / 'skills' / name
        assert (canonical / 'SKILL.md').is_file()
        expected = {p.relative_to(canonical).as_posix(): p.read_bytes() for p in canonical.rglob('*') if p.is_file()}
        for prefix in ('.agents/skills', '.claude/skills', 'src/cv_toolkit/assets/skills'):
            folder = root / prefix / name
            actual = {p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob('*') if p.is_file()}
            assert actual == expected, f'run tools/sync_skills.py for {prefix}/{name}'
