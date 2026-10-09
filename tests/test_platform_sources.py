"""The workbench bundles sources from three repositories; release and local
modes must each produce exactly those sources or fail loudly."""

import importlib.util
import io
import tarfile
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "platform_sources", Path(__file__).resolve().parents[1] / "jupyter" / "platform_sources.py"
)
ps = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ps)

MARKERS = {name: marker for name, (_, _, marker) in ps.REPOS.items()}
VERSIONS = {"SDK_VERSION": "v0.2.0", "AGENT_RUNTIME_VERSION": "v0.1.0",
            "PIPELINE_RUNNER_VERSION": "v0.1.0"}


def archive(files: dict[str, bytes], top: str = "repo-0.1.0") -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(f"{top}/{name}")
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buffer.getvalue()


def fake_fetcher(calls):
    def fetch(url):
        calls.append(url)
        repo = url.split("/kiongahq/")[1].split("/")[0]
        name = next(n for n, (r, _, _) in ps.REPOS.items() if r == repo)
        return archive({MARKERS[name]: b"x", "README.md": b"r"})
    return fetch


def test_local_mode_accepts_complete_checkouts(tmp_path):
    for name, marker in MARKERS.items():
        (tmp_path / name / marker).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name / marker).write_text("x")
    assert ps.main(["x", "local", str(tmp_path)]) == 0


def test_local_mode_refuses_a_missing_checkout(tmp_path, capsys):
    (tmp_path / "sdk").mkdir()
    assert ps.main(["x", "local", str(tmp_path)]) == 1
    assert "--build-context sdk=" in capsys.readouterr().err


def test_release_mode_downloads_pinned_tags(tmp_path, monkeypatch):
    for key, value in VERSIONS.items():
        monkeypatch.setenv(key, value)
    calls = []
    assert ps.main(["x", "release", str(tmp_path)], fetcher=fake_fetcher(calls)) == 0
    assert calls == [
        "https://github.com/kiongahq/sdk-python/archive/refs/tags/v0.2.0.tar.gz",
        "https://github.com/kiongahq/agent-runtime/archive/refs/tags/v0.1.0.tar.gz",
        "https://github.com/kiongahq/pipeline-runner/archive/refs/tags/v0.1.0.tar.gz",
    ]
    for name, marker in MARKERS.items():
        assert (tmp_path / name / marker).is_file()       # top-level dir stripped


@pytest.mark.parametrize("version", ["", "main", "0.2.0"])
def test_release_mode_requires_a_tag(tmp_path, monkeypatch, version):
    for key, value in VERSIONS.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("SDK_VERSION", version)
    assert ps.main(["x", "release", str(tmp_path)], fetcher=fake_fetcher([])) == 1


def test_release_mode_refuses_to_mix_with_local_sources(tmp_path, monkeypatch):
    for key, value in VERSIONS.items():
        monkeypatch.setenv(key, value)
    (tmp_path / "sdk").mkdir()
    (tmp_path / "sdk" / "stale.py").write_text("x")
    assert ps.main(["x", "release", str(tmp_path)], fetcher=fake_fetcher([])) == 1


def test_unsafe_archive_members_are_rejected(tmp_path):
    with pytest.raises(SystemExit):
        ps.extract(archive({"../../etc/evil": b"x"}), tmp_path / "out")
    assert not (tmp_path / "etc").exists()


def test_bad_arguments_print_usage():
    assert ps.main(["x"]) == 2
    assert ps.main(["x", "both", "/tmp"]) == 2
