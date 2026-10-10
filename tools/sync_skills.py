"""Generate native host and wheel copies from the sole authored skills/ tree."""
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ('experience-capture', 'application-materials', 'resume-review', 'cover-letter-review')
TARGETS = ('.agents/skills', '.claude/skills', 'src/cv_toolkit/assets/skills')


def sync(root=ROOT, *, check=False):
    root = Path(root).resolve()
    writes = []
    for name in SKILLS:
        source = root / 'skills' / name
        if not (source / 'SKILL.md').is_file():
            raise ValueError(f'missing canonical manifest: skills/{name}/SKILL.md')
        expected = {p.relative_to(source): p.read_bytes() for p in source.rglob('*') if p.is_file()}
        for prefix in TARGETS:
            folder = root / prefix / name
            if not folder.resolve().is_relative_to(root):
                raise ValueError('generated directory escapes repository')
            actual = {p.relative_to(folder): p.read_bytes() for p in folder.rglob('*') if p.is_file()}
            if actual.keys() - expected.keys():
                raise ValueError(f'unexpected generated files in {prefix}/{name}; review them manually')
            for relative, raw in expected.items():
                path = folder / relative
                if not path.resolve().is_relative_to(root):
                    raise ValueError('generated file escapes repository')
                if actual.get(relative) != raw:
                    writes.append((path, raw))
    if check:
        if writes:
            raise ValueError('skill copies are stale; run python tools/sync_skills.py')
    else:
        for path, raw in writes:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    return len(writes)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    try:
        count = sync(check=args.check)
    except (ValueError, OSError) as error:
        parser.exit(1, str(error) + '\n')
    print('skill copies current' if args.check else f'updated {count} generated skill files')
