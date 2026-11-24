#!/usr/bin/env python3
"""Regenerate the hash-locked dependency files of the Kionga SDK for both images.

    python scripts/lock_sdk_dependencies.py

Run it after changing SDK_VERSION (and SDK_WHEEL_SHA256) in the Dockerfiles, or to
pick up newer releases of the SDK's dependencies. It needs `uv` on PATH
(`pip install uv`) and network access to PyPI and GitHub.

It writes two files, each the full dependency closure of the pinned SDK release with
a SHA-256 for every file of every package, which the Dockerfiles install with
`pip install --require-hashes`:

  ide/sdk-requirements.txt      the core SDK (httpx, pydantic and theirs)
  jupyter/sdk-requirements.txt  the SDK with the agents and huggingface extras

The SDK itself is left out of both: the IDE image installs its release wheel by
digest and the Jupyter image installs the tagged source.

The locks are universal (`uv pip compile --universal`): one file carries the hashes
for linux/amd64 and linux/arm64, so the same lock serves CI and a build on an Arm
laptop.

The Jupyter lock is resolved in two steps. The image installs JupyterLab, MLflow,
Prefect and others before the SDK, and they share packages with the SDK's closure
(websockets, packaging, protobuf). Resolving the SDK alone can pick a version one of
them refuses. So the first step resolves the SDK together with every package the
Dockerfile installs, and the second locks the SDK's closure to the versions the
first step chose.
"""

from __future__ import annotations

import re
import shutil
import subprocess  # nosec B404
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON_VERSION = "3.11"  # python:3.11-slim (Jupyter) and Debian bookworm (IDE)
COMMAND = "python scripts/lock_sdk_dependencies.py"
WHEEL = "https://github.com/kiongahq/sdk-python/releases/download/v{v}/kionga-{v}-py3-none-any.whl"
ARCHIVE = "https://github.com/kiongahq/sdk-python/archive/refs/tags/v{v}.tar.gz"
JUPYTER_EXTRAS = "agents,huggingface"
IDE_LOCK = ROOT / "ide" / "sdk-requirements.txt"
JUPYTER_LOCK = ROOT / "jupyter" / "sdk-requirements.txt"


def sdk_version(dockerfile: str) -> str:
    """The release in `ARG SDK_VERSION=v<release>`, without the v."""
    found = re.search(r"^ARG SDK_VERSION=v([0-9]+\.[0-9]+\.[0-9]+)$", dockerfile, re.M)
    if not found:
        raise SystemExit("no `ARG SDK_VERSION=v<release>` line in the Dockerfile")
    return found.group(1)


def image_packages(dockerfile: str) -> list[str]:
    """Every package requirement the Dockerfile's `pip install` commands name in quotes.

    The SDK itself, paths (its source directory) and URLs are left out: the SDK is
    added by the caller at the pinned release.
    """
    lines = [line for line in dockerfile.replace("\\\n", " ").splitlines()
             if not line.lstrip().startswith("#")]
    packages: list[str] = []
    for line in lines:
        for command in re.split(r"&&|\|\||;", line):
            if not re.search(r"\bpip install\b", command):
                continue
            for spec in re.findall(r'"([^"]+)"', command):
                name = re.match(r"([A-Za-z0-9][A-Za-z0-9._-]*)(\[[^\]]*\])?\s*(==|>=|<=|~=|!=|<|>|$)", spec)
                if name and name.group(1).lower() != "kionga":
                    packages.append(spec)
    return packages


def header(version: str, what: str, dockerfile: str) -> str:
    return (f"# Hash-locked dependencies of the Kionga SDK v{version} ({what}), installed by\n"
            f"# {dockerfile} with `pip install --require-hashes`. Do not edit by hand.\n"
            f"# Regenerate with: {COMMAND}\n")


def uv(cwd: Path, *arguments: str) -> None:
    # A fixed argument list, no shell.
    subprocess.run(["uv", "pip", "compile", "--quiet", "--universal",  # nosec B603 B607
                    "--python-version", PYTHON_VERSION, "--custom-compile-command", COMMAND,
                    *arguments], cwd=cwd, check=True)


def lock(cwd: Path, requirement: str, target: Path, text: str, *arguments: str) -> None:
    (cwd / "sdk.in").write_text(requirement + "\n")
    uv(cwd, "sdk.in", "--generate-hashes", "--no-emit-package", "kionga", "--output-file", "lock.txt",
       *arguments)
    target.write_text(text + (cwd / "lock.txt").read_text())


def main() -> int:
    if shutil.which("uv") is None:
        raise SystemExit("uv is not on PATH; install it with `pip install uv`")
    jupyter = (ROOT / "jupyter" / "Dockerfile").read_text()
    version = sdk_version(jupyter)
    if sdk_version((ROOT / "ide" / "Dockerfile").read_text()) != version:
        raise SystemExit("ide/Dockerfile and jupyter/Dockerfile pin different SDK_VERSION values")

    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        lock(work, "kionga @ " + WHEEL.format(v=version), IDE_LOCK,
             header(version, "core package", "ide/Dockerfile"))

        sdk = f"kionga[{JUPYTER_EXTRAS}] @ " + ARCHIVE.format(v=version)
        packages = image_packages(jupyter)
        if not packages:
            raise SystemExit("found no pip packages in jupyter/Dockerfile")
        (work / "image.in").write_text("\n".join([sdk, *packages]) + "\n")
        uv(work, "image.in", "--output-file", "jupyter-image-packages.txt")
        lock(work, sdk, JUPYTER_LOCK,
             header(version, f"extras {JUPYTER_EXTRAS}", "jupyter/Dockerfile"),
             "--constraint", "jupyter-image-packages.txt")
    for path in (IDE_LOCK, JUPYTER_LOCK):
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
