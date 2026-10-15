"""Release artifacts must contain only the intended distributable files."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import posixpath
import re
import stat
import tarfile
import zipfile
from urllib.parse import urlsplit

import pytest


ROOT = Path(__file__).resolve().parents[1]


def builder():
    path = ROOT / "tools/build_release.py"
    assert path.is_file(), "the repeatable release builder is missing"
    spec = importlib.util.spec_from_file_location("build_release", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def wheel(path, names):
    with zipfile.ZipFile(path, "w") as archive:
        for name in names:
            archive.writestr(name, b"synthetic package fixture\n")


def sdist(path, names, *, symlink=None):
    with tarfile.open(path, "w:gz") as archive:
        for name in names:
            content = b"synthetic package fixture\n"
            info = tarfile.TarInfo(name)
            info.size = len(content)
            archive.addfile(info, io.BytesIO(content))
        if symlink:
            info = tarfile.TarInfo(symlink)
            info.type = tarfile.SYMTYPE
            info.linkname = "../../outside.txt"
            archive.addfile(info)


def test_release_rejects_existing_destination_before_build(tmp_path):
    target = tmp_path / "release"
    target.mkdir()
    marker = target / "keep.txt"
    marker.write_text("keep", encoding="utf-8")
    with pytest.raises(ValueError, match="new directory"):
        builder().build_release(ROOT, target)
    assert marker.read_text(encoding="utf-8") == "keep"
    assert list(target.iterdir()) == [marker]


@pytest.mark.parametrize("extra", ["cv_toolkit/profile/evidence.json", ".env", "../outside.txt"])
def test_wheel_rejects_unexpected_or_unsafe_member(tmp_path, extra):
    path = tmp_path / "package.whl"
    wheel(path, ["cv_toolkit/__init__.py", extra])
    with pytest.raises(ValueError, match="unexpected|unsafe"):
        builder().inspect_archive(path, {"cv_toolkit/__init__.py"})


def test_sdist_rejects_symbolic_link(tmp_path):
    path = tmp_path / "package.tar.gz"
    sdist(path, ["package/README.md"], symlink="package/private.txt")
    with pytest.raises(ValueError, match="link|regular"):
        builder().inspect_archive(path, {"package/README.md", "package/private.txt"})


def test_wheel_rejects_symbolic_link_disguised_as_directory(tmp_path):
    path = tmp_path / "package.whl"
    with zipfile.ZipFile(path, "w") as archive:
        info = zipfile.ZipInfo("cv_toolkit/")
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, "../outside")
        archive.writestr("cv_toolkit/__init__.py", "")
    with pytest.raises(ValueError, match="link"):
        builder().inspect_archive(path, {"cv_toolkit/__init__.py"})


def test_archive_requires_expected_package_assets(tmp_path):
    path = tmp_path / "package.whl"
    wheel(path, ["cv_toolkit/__init__.py"])
    with pytest.raises(ValueError, match="missing"):
        builder().inspect_archive(path, {"cv_toolkit/__init__.py", "cv_toolkit/assets/ats.css"})


def test_manifest_and_checksums_match_actual_artifact_bytes(tmp_path):
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    wheel_path = artifact_dir / "resume_toolkit-0.2.0-py3-none-any.whl"
    source_path = artifact_dir / "resume_toolkit-0.2.0.tar.gz"
    wheel(wheel_path, ["cv_toolkit/__init__.py"])
    sdist(source_path, ["resume_toolkit-0.2.0/src/cv_toolkit/__init__.py"])
    destination = tmp_path / "release"
    expected = {
        "wheel": {"cv_toolkit/__init__.py"},
        "sdist": {"resume_toolkit-0.2.0/src/cv_toolkit/__init__.py"},
    }
    install_guide = b"# Install this release\n\nSynthetic installation guide.\n"
    documentation = {"INSTALL.md": install_guide, "docs/agent-hosts.md": b"# Host setup\n"}
    report = builder().publish_artifacts(artifact_dir, destination, "0.2.0", expected, documentation)
    assert report == json.loads((destination / "release-manifest.json").read_text(encoding="utf-8"))
    assert {entry["kind"] for entry in report["artifacts"]} == {"wheel", "sdist"}
    assert (destination / "INSTALL.md").read_bytes() == install_guide
    assert report["installation_guide"]["filename"] == "INSTALL.md"
    assert report["installation_guide"]["sha256"] == hashlib.sha256(install_guide).hexdigest()
    assert {entry["filename"] for entry in report["documentation"]} == set(documentation)
    for entry in report["documentation"]:
        data = (destination / entry["filename"]).read_bytes()
        assert entry["sha256"] == hashlib.sha256(data).hexdigest()
    for artifact in report["artifacts"]:
        data = (destination / artifact["filename"]).read_bytes()
        assert artifact["sha256"] == hashlib.sha256(data).hexdigest()
        assert artifact["size"] == len(data)
        assert set(artifact["members"]) == expected[artifact["kind"]]
    sums = (destination / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
    assert len(sums) == 5
    for line in sums:
        digest, filename = line.split("  ")
        assert digest == hashlib.sha256((destination / filename).read_bytes()).hexdigest()


def test_source_allowlist_rejects_candidate_file_in_package(tmp_path):
    source = tmp_path / "source"
    package = source / "src/cv_toolkit"
    package.mkdir(parents=True)
    (package / "candidate.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="unexpected"):
        builder().release_sources(source)


def test_standalone_install_guide_resolves_document_links():
    source = ('[Host setup](agent-hosts.md#hermes)\n'
              '[Official](https://example.org/skills) [Section](#install)\n'
              '```text\n[example](local.md)\n```\n')
    result = builder().standalone_guide(source.encode()).decode()
    assert '[Host setup](docs/agent-hosts.md#hermes)' in result
    assert '[Official](https://example.org/skills) [Section](#install)' in result
    assert '```text\n[example](local.md)\n```' in result


def test_bundled_usage_documentation_has_no_broken_local_links():
    documents = builder().release_documentation(ROOT)
    assert "INSTALL.md" in documents and "docs/agent-hosts.md" in documents
    assert "skills/application-materials/SKILL.md" in documents
    for filename, raw in documents.items():
        # Ignore executable examples: they can deliberately illustrate paths.
        text = re.sub(r"(?ms)^\s*(```|~~~).*?^\s*\1[^\n]*\n?", "", raw.decode("utf-8"))
        for link in re.findall(r"\]\(([^)]+)\)", text):
            parsed = urlsplit(link)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = posixpath.normpath(posixpath.join(posixpath.dirname(filename), parsed.path))
            assert target in documents, (filename, link)


def test_documentation_rejects_unlisted_local_target(tmp_path):
    module = builder()
    for filename in module.DOCUMENT_FILES:
        path = tmp_path / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Public usage documentation\n", encoding="utf-8")
    (tmp_path / "docs/deployment.md").write_text("[Private](../private/notes.md)\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unlisted|missing"):
        module.release_documentation(tmp_path)
