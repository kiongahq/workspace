#!/usr/bin/env python3
"""Put the Kionga Python sources the workbench bundles under one directory.

The Jupyter image ships the SDK plus the runnable platform modules (agents,
features, realtime from agent-runtime; pipelines from pipeline-runner) so
notebooks can drive the whole stack. They live in their own repositories:

  release  download each repository's tagged source archive from GitHub
  local    use sibling checkouts passed as BuildKit named contexts

Usage: platform_sources.py <release|local> <src-dir>
Versions come from SDK_VERSION, AGENT_RUNTIME_VERSION, PIPELINE_RUNNER_VERSION.
"""

from __future__ import annotations

import io
import os
import sys
import tarfile
import urllib.request
from pathlib import Path

REPOS = {
    # directory under <src-dir>: (repository, version variable, marker file)
    "sdk": ("sdk-python", "SDK_VERSION", "pyproject.toml"),
    "agent-runtime": ("agent-runtime", "AGENT_RUNTIME_VERSION", "agent_runtime/__init__.py"),
    "pipeline-runner": ("pipeline-runner", "PIPELINE_RUNNER_VERSION", "pipelines/__init__.py"),
}
ARCHIVE = "https://github.com/kiongahq/{repo}/archive/refs/tags/{version}.tar.gz"


def extract(data: bytes, dest: Path) -> None:
    """Extract a GitHub source archive, dropping its top-level directory."""
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        for member in archive.getmembers():
            parts = Path(member.name).parts[1:]
            if not parts:
                continue
            if any(p == ".." for p in parts) or member.issym() or member.islnk():
                raise SystemExit(f"refusing unsafe archive member: {member.name}")
            member.name = str(Path(*parts))
            archive.extract(member, dest, filter="data")


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as response:  # noqa: S310 (fixed https URL)
        return response.read()


def main(argv: list[str], fetcher=fetch) -> int:
    if len(argv) != 3 or argv[1] not in {"release", "local"}:
        print(__doc__, file=sys.stderr)
        return 2
    mode, root = argv[1], Path(argv[2])
    for name, (repo, version_var, marker) in REPOS.items():
        dest = root / name
        if mode == "local":
            if not (dest / marker).is_file():
                print(f"PLATFORM_SOURCE=local needs --build-context {name}=<{repo} checkout> "
                      f"(missing {name}/{marker})", file=sys.stderr)
                return 1
            continue
        version = os.environ.get(version_var, "")
        if not version.startswith("v"):
            print(f"{version_var} must be a release tag like v1.2.3, got {version!r}", file=sys.stderr)
            return 1
        if dest.exists() and any(dest.iterdir()):
            print(f"{dest} is not empty; refusing to mix local and release sources",
                  file=sys.stderr)
            return 1
        extract(fetcher(ARCHIVE.format(repo=repo, version=version)), dest)
        if not (dest / marker).is_file():
            print(f"{repo} {version} archive has no {marker}", file=sys.stderr)
            return 1
        print(f"{repo} {version} -> {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
