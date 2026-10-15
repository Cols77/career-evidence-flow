"""Build checked wheel/sdist artifacts into a NEW explicit output directory.

Install the dev extra first: python -m pip install -e ".[dev]".
The exact path allowlist prevents accidental packaging of workspace files; it
does not replace the external private-content scan required before publication.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import zipfile
from urllib.parse import unquote, urlsplit, urlunsplit


ROOT = Path(__file__).resolve().parents[1]
# Adding a distributable file requires deliberately extending this allowlist.
MODULES = """
__init__ application artifact_audit ats bootstrap cli codex_hooks deployment
evidence gallery jev_review jev_review_cli letter_check onboarding projection
questions records render resume_layout workspace
""".split()
STYLES = "ats branded letter minimal modern resume-layout".split()
SKILLS = {
    "application-materials": ("application-records", "drafting-workflow", "voice-and-artifacts"),
    "experience-capture": ("evidence-and-interview",),
    "resume-review": ("review-packet", "rubric"),
    "cover-letter-review": ("review-packet", "rubric"),
}
PACKAGE_FILES = {f"{name}.py" for name in MODULES}
PACKAGE_FILES.update(f"assets/{style}.css" for style in STYLES)
PACKAGE_FILES.update(("assets/template.html", "assets/gallery.html", "assets/hook/__init__.py", "assets/hook/plugin.yaml"))
for _profile in ("developer", "researcher", "showcase"):
    for _filename in ("cvtool.toml", "evidence.json", "projection.json", "registry.json", "resume.md"):
        PACKAGE_FILES.add(f"assets/examples/{_profile}/{_filename}")
    PACKAGE_FILES.add(f"assets/examples/{_profile}/" + ("README.md" if _profile == "showcase" else "letter.md"))
for _skill, _references in SKILLS.items():
    PACKAGE_FILES.add(f"assets/skills/{_skill}/SKILL.md")
    PACKAGE_FILES.update(f"assets/skills/{_skill}/references/{name}.md" for name in _references)
ROOT_FILES = {"pyproject.toml", "README.md", "MANIFEST.in"}
EGG_FILES = {"PKG-INFO", "SOURCES.txt", "dependency_links.txt", "entry_points.txt", "requires.txt", "top_level.txt"}
WHEEL_FILES = {"METADATA", "WHEEL", "RECORD", "entry_points.txt", "top_level.txt"}
DOCUMENT_FILES = {f"docs/{name}.md" for name in (
    "deployment", "agent-hosts", "application-workflow", "codex-workflows",
    "getting-started", "optional-jev-review", "privacy", "resume-visuals",
    "review-and-release", "workflow",
)}
DOCUMENT_FILES.update(path.removeprefix("assets/") for path in PACKAGE_FILES
                      if path.startswith("assets/skills/"))


def release_sources(root):
    """Reject unexpected package files and return the exact distributable inputs."""
    root = Path(root).resolve()
    package = root / "src/cv_toolkit"
    actual = set()
    for path in package.rglob("*"):
        relative = path.relative_to(package)
        if "__pycache__" in relative.parts:
            continue
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError(f"unsafe source link: {relative.as_posix()}")
        if path.is_file():
            actual.add(relative.as_posix())
    unexpected = actual - PACKAGE_FILES
    if unexpected:
        raise ValueError(f"unexpected package files: {', '.join(sorted(unexpected))}")
    missing = PACKAGE_FILES - actual
    if missing:
        raise ValueError(f"missing package files: {', '.join(sorted(missing))}")
    result = ROOT_FILES | {f"src/cv_toolkit/{path}" for path in PACKAGE_FILES}
    for relative in result:
        path = root / relative
        if path.is_symlink() or not path.resolve().is_relative_to(root) or not path.is_file():
            raise ValueError(f"missing or unsafe release input: {relative}")
    return result


def inspect_archive(path, expected):
    """Read archive metadata without extracting anything; require the exact file set."""
    found = set()
    seen = set()

    def member(name, directory, regular):
        normalized = name.rstrip("/")
        parts = PurePosixPath(normalized)
        if (not normalized or "\\" in name or ":" in name or parts.is_absolute()
                or ".." in parts.parts or str(parts) != normalized or name in seen):
            raise ValueError(f"unsafe archive member: {name}")
        seen.add(name)
        if directory:
            if not any(candidate.startswith(normalized + "/") for candidate in expected):
                raise ValueError(f"unexpected archive directory: {name}")
        elif not regular:
            raise ValueError(f"archive link or non-regular file: {name}")
        elif name not in expected:
            raise ValueError(f"unexpected archive member: {name}")
        else:
            found.add(name)

    if path.name.endswith(".whl"):
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                mode = info.external_attr >> 16
                if stat.S_ISLNK(mode):
                    raise ValueError(f"archive link: {info.filename}")
                regular = stat.S_IFMT(mode) in (0, stat.S_IFREG)
                member(info.filename, info.is_dir(), regular)
    else:
        with tarfile.open(path, "r:gz") as archive:
            for info in archive.getmembers():
                member(info.name, info.isdir(), info.isfile())
    if found != expected:
        raise ValueError(f"missing archive members: {', '.join(sorted(expected - found))}")
    return sorted(found)


def publish_artifacts(artifact_dir, output, version, expected, documentation):
    """Validate both archives before creating the final directory and checksums."""
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError("output must be a new directory")
    paths = sorted(Path(artifact_dir).iterdir())
    if (len(paths) != 2 or sum(path.name.endswith(".whl") for path in paths) != 1
            or sum(path.name.endswith(".tar.gz") for path in paths) != 1):
        raise ValueError("build must produce exactly one wheel and one source distribution")
    if "INSTALL.md" not in documentation or set(documentation) - (DOCUMENT_FILES | {"INSTALL.md"}):
        raise ValueError("missing installation guide or unlisted release documentation")
    document_records = [{"filename": filename, "size": len(raw),
                         "sha256": hashlib.sha256(raw).hexdigest()}
                        for filename, raw in sorted(documentation.items())]
    guide_record = next(entry for entry in document_records if entry["filename"] == "INSTALL.md")
    report = {"distribution": "resume-toolkit", "version": version, "artifacts": [],
              "installation_guide": guide_record, "documentation": document_records}
    for path in paths:
        kind = "wheel" if path.name.endswith(".whl") else "sdist"
        members = inspect_archive(path, expected[kind])
        raw = path.read_bytes()
        report["artifacts"].append({"kind": kind, "filename": path.name, "size": len(raw),
                                    "sha256": hashlib.sha256(raw).hexdigest(), "members": members})
    output.mkdir(parents=True, exist_ok=False)
    for path in paths:
        shutil.copyfile(path, output / path.name)
    for filename, raw in documentation.items():
        target = output / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    manifest = output / "release-manifest.json"
    manifest.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    checksums = [f"{entry['sha256']}  {entry['filename']}" for entry in report["artifacts"]]
    checksums.extend(f"{entry['sha256']}  {entry['filename']}" for entry in document_records)
    checksums.append(f"{hashlib.sha256(manifest.read_bytes()).hexdigest()}  {manifest.name}")
    (output / "SHA256SUMS").write_text("\n".join(checksums) + "\n", encoding="utf-8")
    return report


def _map_document_links(raw, transform):
    """Visit prose links in the supported Markdown docs; leave fenced examples alone."""
    fence = None
    lines = []
    for line in raw.decode('utf-8').splitlines(keepends=True):
        marker = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line)
        if marker:
            token, suffix = marker.groups()
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence) and not suffix.strip():
                fence = None
        elif fence is None:
            line = re.sub(r'\]\(([^)]+)\)', lambda match: '](' + transform(match.group(1)) + ')', line)
        lines.append(line)
    return ''.join(lines).encode('utf-8')


def standalone_guide(raw):
    """Point INSTALL.md at the bundled docs while preserving external URLs/examples."""
    def link(target):
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or not parsed.path:
            return target
        path = posixpath.normpath(posixpath.join('docs', parsed.path))
        return urlunsplit(('', '', path, parsed.query, parsed.fragment))
    return _map_document_links(raw, link)


def release_documentation(root):
    """Bundle the curated usage docs and references with their relative paths intact."""
    root = Path(root).resolve()
    documents = {}
    for filename in sorted(DOCUMENT_FILES):
        path = root / filename
        if path.is_symlink() or not path.resolve().is_relative_to(root) or not path.is_file():
            raise ValueError(f'missing or unsafe release documentation: {filename}')
        documents[filename] = path.read_bytes()
    documents['INSTALL.md'] = standalone_guide(documents['docs/deployment.md'])
    for filename, raw in documents.items():
        def check(target):
            parsed = urlsplit(target)
            if not parsed.scheme and not parsed.netloc and parsed.path:
                relative = posixpath.normpath(posixpath.join(posixpath.dirname(filename), unquote(parsed.path)))
                if relative not in documents:
                    raise ValueError(f'unlisted or missing documentation link in {filename}: {target}')
            return target
        _map_document_links(raw, check)
    return documents


def build_release(root, output):
    root, output = Path(root).resolve(), Path(output).absolute()
    if output.exists() or output.is_symlink():
        raise ValueError("output must be a new directory")
    inputs = release_sources(root)
    documentation = release_documentation(root)
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    version = project["version"]
    if project["name"] != "resume-toolkit" or not all(part.isdigit() for part in version.split(".")):
        raise ValueError("unexpected release distribution name or version")
    subprocess.run([sys.executable, str(root / "tools/sync_skills.py"), "--check"], cwd=root, check=True)
    prefix = f"resume_toolkit-{version}"
    expected = {
        "wheel": {f"cv_toolkit/{path}" for path in PACKAGE_FILES}
        | {f"{prefix}.dist-info/{name}" for name in WHEEL_FILES},
        "sdist": {f"{prefix}/{path}" for path in inputs}
        | {f"{prefix}/{name}" for name in ("PKG-INFO", "setup.cfg")}
        | {f"{prefix}/src/resume_toolkit.egg-info/{name}" for name in EGG_FILES},
    }
    # A clean source copy avoids cached build files or unrelated checkout data.
    with tempfile.TemporaryDirectory(prefix="resume-toolkit-release-") as temporary:
        staging = Path(temporary) / "source"
        for relative in sorted(inputs):
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(root / relative, target)
        artifacts = Path(temporary) / "artifacts"
        subprocess.run([sys.executable, "-m", "build", "--outdir", str(artifacts), str(staging)], check=True)
        return publish_artifacts(artifacts, output, version, expected, documentation)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="new destination for wheel, sdist and checksums")
    args = parser.parse_args(argv)
    try:
        report = build_release(ROOT, args.output)
    except (ValueError, OSError, subprocess.CalledProcessError, tarfile.TarError, zipfile.BadZipFile) as error:
        parser.exit(1, str(error) + "\n")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
