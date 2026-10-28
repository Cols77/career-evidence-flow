"""Fail-closed scanner. The private denylist must stay outside this repository.

This supplements a manual allowlist review; a passing scan cannot certify that
arbitrary unknown personal information or obfuscated secrets are absent.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


TEXT_SUFFIXES = {'.js', '.py', '.md', '.json', '.toml', '.css', '.html', '.txt', '.yml', '.yaml'}
TEXT_NAMES = {'.gitignore', '.gitattributes', 'LICENSE', 'NOTICE', 'MANIFEST.in'}
CREDENTIALS = re.compile(r'gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|AKIA[A-Z0-9]{16}|-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----')


def _git(repo: Path, *args: str) -> bytes:
    result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True)
    if result.returncode:
        raise ValueError('git.failure')
    return result.stdout


def _rules(repo: Path, path: Path) -> list[tuple[str, str]]:
    resolved = path.resolve(strict=True)
    if resolved.is_relative_to(repo):
        raise ValueError('denylist.internal')
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError('denylist.invalid')
            obj[key] = value
        return obj
    obj = json.loads(resolved.read_text(encoding='utf-8'), object_pairs_hook=unique)
    if not isinstance(obj, dict) or set(obj) != {'rules'} or not isinstance(obj['rules'], list) or not obj['rules']:
        raise ValueError('denylist.invalid')
    rules = []
    ids = set()
    for entry in obj['rules']:
        if not isinstance(entry, dict) or set(entry) != {'id', 'token'}:
            raise ValueError('denylist.invalid')
        if any(not isinstance(entry[key], str) or not entry[key].strip() for key in entry):
            raise ValueError('denylist.invalid')
        # Rule names are the only externally supplied value ever reported.
        if not all(c.isascii() and (c.isalnum() or c in '._-') for c in entry['id']) or entry['id'] in ids:
            raise ValueError('denylist.invalid')
        ids.add(entry['id'])
        rules.append((entry['id'], entry['token'].casefold()))
    return rules


def scan(repo: Path, denylist: Path, mode: str) -> dict:
    result = {'status': 'blocked', 'mode': mode, 'files_scanned': 0, 'findings': []}
    findings = set()
    rules = []
    def finding(path, rule):
        if any(token in path.casefold() for _, token in rules) or CREDENTIALS.search(path):
            path = '<redacted-path-' + hashlib.sha256(path.encode()).hexdigest()[:12] + '>'
        findings.add((path, rule))
    try:
        repo = Path(repo).resolve(strict=True)
        rules = _rules(repo, Path(denylist))
        if mode not in {'staged', 'history', 'worktree'}:
            raise ValueError('mode.invalid')
        root = Path(_git(repo, 'rev-parse', '--show-toplevel').decode().strip()).resolve()
        if root != repo:
            raise ValueError('git.root')

        def inspect(path, data, *, metadata=False):
            if CREDENTIALS.search(path):
                finding(path, 'credential.pattern')
            if not metadata:
                result['files_scanned'] += 1
                parts = Path(path).parts
                lowered = tuple(p.casefold() for p in parts)
                local_claude = ('.claude' in lowered and Path(path).name.casefold() == 'settings.local.json') or any(lowered[i:i + 2] == ('.claude', 'hooks') for i in range(len(lowered) - 1))
                local_guide = Path(path).name.casefold() == 'resume_toolkit.md'
                if any(p in {'.hermes', '.codex', '.local', 'private', 'user-profile', 'outputs', 'profiles', '.git'} for p in lowered) or local_claude or local_guide or Path(path).name.casefold().startswith('.env') or Path(path).suffix.casefold() in {'.pem', '.key', '.pfx', '.p12'}:
                    finding(path, 'sensitive.path')
                if Path(path).suffix.casefold() not in TEXT_SUFFIXES and Path(path).name not in TEXT_NAMES:
                    finding(path, 'unexpected.binary')
            texts = [path.casefold()]
            decoded = False
            for encoding in ('utf-8', 'utf-16'):
                try:
                    text = data.decode(encoding)
                    texts.append(text.casefold())
                    if CREDENTIALS.search(text):
                        finding(path, 'credential.pattern')
                    if '\x00' not in text:
                        decoded = True
                except UnicodeError:
                    pass
            if not metadata and not decoded:
                finding(path, 'unexpected.binary')
            for rule, token in rules:
                if any(token in text for text in texts):
                    finding(path, rule)

        if mode == 'staged':
            entries = _git(repo, 'ls-files', '--stage', '-z').split(b'\0')
            for entry in filter(None, entries):
                descriptor, rawpath = entry.split(b'\t', 1)
                bits = descriptor.split()
                if bits[0] not in {b'100644', b'100755'} or bits[2] != b'0':
                    finding(rawpath.decode('utf-8'), 'unsupported.git-entry')
            paths = _git(repo, 'diff', '--cached', '--name-only', '--diff-filter=ACMR', '-z').split(b'\0')
            for raw in filter(None, paths):
                path = raw.decode('utf-8')
                inspect(path, _git(repo, 'show', ':' + path))
        elif mode == 'worktree':
            paths = _git(repo, 'ls-files', '--cached', '--others', '--exclude-standard', '-z').split(b'\0')
            for raw in sorted(set(filter(None, paths))):
                path = raw.decode('utf-8')
                original = repo / path
                target = original.resolve(strict=True)
                if not target.is_relative_to(repo) or original.is_symlink():
                    raise ValueError('path.escape')
                inspect(path, target.read_bytes())
        else:
            commits = _git(repo, 'rev-list', '--all').decode().splitlines()
            if not commits:
                raise ValueError('history.empty')
            seen = set()
            for ref in _git(repo, 'for-each-ref', '--format=%(refname)').decode().splitlines():
                inspect('<ref-metadata>', ref.encode(), metadata=True)
            for commit in commits:
                inspect('<commit-metadata>', _git(repo, 'cat-file', 'commit', commit), metadata=True)
                for entry in filter(None, _git(repo, 'ls-tree', '-r', '-z', commit).split(b'\0')):
                    descriptor, rawpath = entry.split(b'\t', 1)
                    bits = descriptor.split()
                    path = rawpath.decode('utf-8')
                    if bits[0] in {b'120000', b'160000'}:
                        finding(path, 'unsupported.git-entry')
                    if bits[1] != b'blob':
                        continue
                    key = (bits[2], path)
                    if key not in seen:
                        seen.add(key)
                        inspect(path, _git(repo, 'cat-file', 'blob', bits[2].decode()))
            known_blobs = {oid.decode() for oid, _ in seen}
            for oid in _git(repo, 'rev-list', '--objects', '--all', '--no-object-names').decode().splitlines():
                if oid not in known_blobs:
                    kind = _git(repo, 'cat-file', '-t', oid).strip()
                    if kind == b'blob':
                        inspect('<reachable-blob>', _git(repo, 'cat-file', 'blob', oid))
                    elif kind == b'tag':
                        inspect('<tag-metadata>', _git(repo, 'cat-file', 'tag', oid), metadata=True)
            for tag in _git(repo, 'for-each-ref', '--format=%(objectname) %(objecttype) %(refname)', 'refs/tags').decode().splitlines():
                oid, kind, ref = tag.split(' ', 2)
                inspect('<tag-metadata>', ref.encode(), metadata=True)
                if kind == 'tag':
                    inspect('<tag-metadata>', _git(repo, 'cat-file', 'tag', oid), metadata=True)
        result['status'] = 'blocked' if findings else 'ok'
    except (OSError, ValueError, UnicodeError, RecursionError, subprocess.SubprocessError):
        finding('<scan>', 'scan.incomplete')
    result['findings'] = [{'path': path, 'rule_id': rule} for path, rule in sorted(findings)]
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--denylist', type=Path, required=True)
    parser.add_argument('--mode', choices=('staged', 'history', 'worktree'), required=True)
    args = parser.parse_args(argv)
    result = scan(args.repo, args.denylist, args.mode)
    print(json.dumps(result, sort_keys=True))
    return 0 if result['status'] == 'ok' else 2


if __name__ == '__main__':
    raise SystemExit(main())
