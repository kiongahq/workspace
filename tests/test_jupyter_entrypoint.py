"""Drive jupyter/entrypoint.sh with every external command stubbed.

PATH holds only stub scripts, so nothing real is mounted, chowned or started:
each stub records its argv and exits 0. Tokens are assembled at runtime so
secret scanners never see a literal credential.
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest

ENTRYPOINT = Path(__file__).resolve().parents[1] / "jupyter/entrypoint.sh"
STUBS = ("mkdir", "id", "chown", "runuser", "mountpoint", "s3fs", "chmod", "cp", "env", "python3", "jupyter")
STRONG_TOKEN = "".join(["0123456789abcdef"] * 3)


def _write_stub(directory: Path, name: str, log: Path) -> None:
    body = {
        # Not root, so the entrypoint skips chown/runuser.
        "id": 'echo 1000\n',
        # Nothing is mounted yet.
        "mountpoint": 'exit 1\n',
    }.get(name, "exit 0\n")
    script = directory / name
    script.write_text(
        "#!/bin/sh\n"
        f"printf '%s' '{name}' >> '{log}'\n"
        f"for argument in \"$@\"; do printf '\\037%s' \"$argument\" >> '{log}'; done\n"
        f"printf '\\n' >> '{log}'\n" + body
    )
    script.chmod(script.stat().st_mode | stat.S_IXUSR)


def run_entrypoint(tmp_path: Path, **environment: str):
    stubs = tmp_path / "stubs"
    stubs.mkdir(exist_ok=True)
    log = tmp_path / "calls.log"
    log.write_text("")
    for name in STUBS:
        _write_stub(stubs, name, log)
    fuse = tmp_path / "fuse"
    fuse.write_text("")
    env = {
        "PATH": str(stubs),
        "HOME": str(tmp_path),
        "KIONGA_FUSE_DEVICE": str(fuse),
        "KIONGA_S3FS_PASSWD_FILE": str(tmp_path / "s3fs-passwd"),
        "S3_MOUNT_ROOT": str(tmp_path / "object-store"),
    }
    env.update(environment)
    result = subprocess.run(["/bin/sh", str(ENTRYPOINT)], env=env, capture_output=True, text=True, timeout=30)
    calls = [line.split("\x1f") for line in log.read_text().splitlines() if line]
    return result, calls


def _jupyter_argv(calls):
    (argv,) = [call for call in calls if call[0] == "jupyter"]
    return argv


OPTIONAL_MOUNTS = {"S3_MOUNT_OPTIONAL": "true"}


def test_missing_token_exits_non_zero_and_names_the_variable(tmp_path):
    result, calls = run_entrypoint(tmp_path, **OPTIONAL_MOUNTS)
    assert result.returncode != 0
    assert "JUPYTER_TOKEN" in result.stderr
    assert not [call for call in calls if call[0] in ("jupyter", "env", "s3fs")]


@pytest.mark.parametrize("token", ["mlaiops-local", "x" * 31, "short"])
def test_known_default_or_short_token_is_rejected(tmp_path, token):
    result, calls = run_entrypoint(tmp_path, JUPYTER_TOKEN=token, **OPTIONAL_MOUNTS)
    assert result.returncode != 0
    assert "JUPYTER_TOKEN" in result.stderr and "32" in result.stderr
    assert token not in result.stderr  # the token itself is never echoed
    assert not [call for call in calls if call[0] == "jupyter"]


def test_strong_token_starts_jupyter_on_all_interfaces(tmp_path):
    result, calls = run_entrypoint(tmp_path, JUPYTER_TOKEN=STRONG_TOKEN, **OPTIONAL_MOUNTS)
    assert result.returncode == 0, result.stderr
    argv = _jupyter_argv(calls)
    assert "--ip=0.0.0.0" in argv
    assert f"--IdentityProvider.token={STRONG_TOKEN}" in argv
    assert "--ServerApp.trust_xheaders=True" in argv
    assert not any("mlaiops-local" in argument for argument in argv)


@pytest.mark.parametrize("token", ["", "mlaiops-local"])
def test_insecure_local_mode_binds_loopback_only(tmp_path, token):
    result, calls = run_entrypoint(tmp_path, JUPYTER_TOKEN=token, KIONGA_ALLOW_INSECURE_LOCAL="true",
                                   KIONGA_JUPYTER_IP="0.0.0.0", **OPTIONAL_MOUNTS)
    assert result.returncode == 0, result.stderr
    argv = _jupyter_argv(calls)
    assert "--ip=127.0.0.1" in argv and "--ip=0.0.0.0" not in argv
    assert "KIONGA_ALLOW_INSECURE_LOCAL" in result.stderr


def test_trust_xheaders_is_configurable(tmp_path):
    result, calls = run_entrypoint(tmp_path, JUPYTER_TOKEN=STRONG_TOKEN, KIONGA_JUPYTER_TRUST_XHEADERS="false",
                                   **OPTIONAL_MOUNTS)
    assert result.returncode == 0, result.stderr
    assert "--ServerApp.trust_xheaders=False" in _jupyter_argv(calls)
    result, _ = run_entrypoint(tmp_path, JUPYTER_TOKEN=STRONG_TOKEN, KIONGA_JUPYTER_TRUST_XHEADERS="maybe",
                               **OPTIONAL_MOUNTS)
    assert result.returncode != 0


def test_entrypoint_is_posix_sh():
    assert subprocess.run(["/bin/sh", "-n", str(ENTRYPOINT)]).returncode == 0
    assert os.access(ENTRYPOINT, os.R_OK)
