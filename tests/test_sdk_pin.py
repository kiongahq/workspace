"""The SDK the images and the tests pin must carry the command line that
`kionga apps` is passed on to (workspace/kionga.py hands it to kionga.cli)."""
import importlib.util
import re
import urllib.error
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
# The first SDK release with kionga.cli, the `kionga apps` command line.
FIRST_WITH_CLI = (0, 3, 2)


def version(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in text.split("."))


def pins() -> tuple[str, str]:
    dockerfile = re.search(r"^ARG SDK_VERSION=v([0-9.]+)$", (ROOT / "jupyter" / "Dockerfile").read_text(), re.M)
    requirements = re.search(r"sdk-python/archive/refs/tags/v([0-9.]+)\.tar\.gz",
                             (ROOT / "requirements-dev.txt").read_text())
    assert dockerfile and requirements, "both pins must be present"
    return dockerfile.group(1), requirements.group(1)


def test_the_image_and_the_tests_pin_the_same_sdk_release():
    image, tests = pins()
    assert image == tests


def ide_dockerfile() -> str:
    return (ROOT / "ide" / "Dockerfile").read_text()


def test_the_ide_image_pins_the_same_sdk_release_as_the_jupyter_image():
    ide = re.search(r"^ARG SDK_VERSION=v([0-9.]+)$", ide_dockerfile(), re.M)
    assert ide, "ide/Dockerfile must declare ARG SDK_VERSION=v<release>"
    assert ide.group(1) == pins()[0]


def test_the_ide_image_installs_the_release_wheel_by_hash():
    text = ide_dockerfile()
    digest = re.search(r"^ARG SDK_WHEEL_SHA256=([0-9a-f]{64})$", text, re.M)
    assert digest, "ARG SDK_WHEEL_SHA256 must be a 64 digit lower case hex digest"
    install = re.search(r"pip install[^\n]*\\\n\s*\"(kionga[^\"]*)\"", text)
    assert install, "the SDK install must be a pip install of a quoted kionga requirement"
    requirement = install.group(1)
    assert requirement == (
        "kionga @ https://github.com/kiongahq/sdk-python/releases/download/${SDK_VERSION}/"
        "kionga-${SDK_VERSION#v}-py3-none-any.whl#sha256=${SDK_WHEEL_SHA256}"), requirement
    assert "[" not in requirement, "the IDE image carries the core SDK only, not the heavy extras"


def test_the_ide_image_installs_the_sdk_before_the_workspace_command_replaces_kionga():
    text = ide_dockerfile()
    assert "python3-pip" in text
    assert text.index("kionga-${SDK_VERSION#v}") < text.index("COPY workspace/kionga.py /usr/local/bin/kionga"), (
        "the SDK's own `kionga` script must be installed first so the workspace command overwrites it")
    assert "RUN kionga apps --help" in text, "the build must prove the passthrough reaches the SDK"


def test_the_pinned_sdk_has_the_command_line_kionga_apps_needs():
    image, _ = pins()
    assert version(image) >= FIRST_WITH_CLI, f"SDK v{image} has no kionga.cli; pin v0.3.2 or later"


def test_the_installed_sdk_provides_kionga_cli():
    # requirements-dev.txt installs the pinned release, so this checks the release itself.
    assert importlib.util.find_spec("kionga.cli") is not None


def test_the_ide_digest_is_the_one_the_sdk_release_published():
    """The release's SHA256SUMS names the wheel's digest. Skipped when GitHub can't be
    reached, so the gate never depends on the network; CI reaches it."""
    text = ide_dockerfile()
    version = re.search(r"^ARG SDK_VERSION=(v[0-9.]+)$", text, re.M).group(1)
    digest = re.search(r"^ARG SDK_WHEEL_SHA256=([0-9a-f]{64})$", text, re.M).group(1)
    url = f"https://github.com/kiongahq/sdk-python/releases/download/{version}/SHA256SUMS"
    try:
        with urllib.request.urlopen(url, timeout=20) as response:  # fixed https release URL
            sums = response.read().decode()
    except urllib.error.HTTPError as error:  # GitHub answered: a missing manifest is a failure
        raise AssertionError(f"{url} answered {error.code}") from error
    except OSError as error:  # no network (URLError is an OSError): the gate must not depend on it
        pytest.skip(f"cannot reach {url}: {error}")
    wheel = f"kionga-{version[1:]}-py3-none-any.whl"
    published = {name.strip().removeprefix("./"): sha for sha, name in
                 (line.split(None, 1) for line in sums.splitlines() if line.strip())}
    assert published.get(wheel) == digest, f"SHA256SUMS of {version} lists {published.get(wheel)} for {wheel}"


# The SDK's dependency closure is hash-locked: scripts/lock_sdk_dependencies.py writes
# one requirements file per image and the Dockerfiles install it with --require-hashes.
LOCKS = {"ide": ("core package", {"httpx", "pydantic", "pydantic-core", "httpcore", "anyio"}),
         "jupyter": ("extras agents,huggingface",
                     {"httpx", "pydantic", "langgraph", "langchain-core", "langchain-openai",
                      "langchain-anthropic", "langfuse", "psycopg", "psycopg-binary",
                      "langgraph-checkpoint-postgres", "huggingface-hub"})}


def lock_text(image: str) -> str:
    path = ROOT / image / "sdk-requirements.txt"
    assert path.is_file(), f"{path.relative_to(ROOT)} is missing; run python scripts/lock_sdk_dependencies.py"
    return path.read_text()


def lock_entries(text: str) -> dict[str, list[str]]:
    """Each requirement of a lock file with its continuation lines, by package name.

    Fails on any line that is not a comment, a `name==version` requirement or one of
    its `--hash` lines, so nothing unpinned or unhashed can hide in the file."""
    entries: dict[str, list[str]] = {}
    current: list[str] | None = None
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith(" "):
            assert current is not None, f"line {number} continues nothing: {line!r}"
            assert re.fullmatch(r"\s+--hash=sha256:[0-9a-f]{64}( \\)?", line), f"line {number}: {line!r}"
            current.append(line)
            continue
        requirement = re.fullmatch(r"([a-z0-9][a-z0-9._-]*)==[A-Za-z0-9.!+_-]+( ; [^\\]+)? \\", line)
        assert requirement, f"line {number} is not a pinned requirement followed by hashes: {line!r}"
        assert requirement.group(1) not in entries, f"{requirement.group(1)} is locked twice"
        current = entries[requirement.group(1)] = []
    return entries


@pytest.mark.parametrize("image", sorted(LOCKS))
def test_the_lock_file_names_the_pinned_sdk_release(image):
    described = re.search(r"^# Hash-locked dependencies of the Kionga SDK v([0-9.]+) \(([^)]+)\)",
                          lock_text(image), re.M)
    assert described, "the lock file must open with the SDK release it was generated for"
    assert described.group(1) == pins()[0], (
        f"{image}/sdk-requirements.txt was generated for SDK v{described.group(1)}; "
        "run python scripts/lock_sdk_dependencies.py")
    assert described.group(2) == LOCKS[image][0]


@pytest.mark.parametrize("image", sorted(LOCKS))
def test_every_locked_requirement_is_pinned_and_hashed(image):
    entries = lock_entries(lock_text(image))
    assert LOCKS[image][1] <= set(entries), f"missing from the lock: {LOCKS[image][1] - set(entries)}"
    for name, hashes in entries.items():
        assert hashes, f"{name} has no --hash line"
    assert "kionga" not in entries, "the SDK itself is installed by the Dockerfile, not from the lock"


def test_the_ide_lock_carries_no_extras():
    assert not {"langgraph", "huggingface-hub", "openai"} & set(lock_entries(lock_text("ide")))


def instructions(dockerfile: str) -> list[str]:
    """Dockerfile instructions with continuations joined and comment lines dropped."""
    lines = [line for line in dockerfile.splitlines() if not line.lstrip().startswith("#")]
    return "\n".join(lines).replace("\\\n", " ").splitlines()


def pip_installs(dockerfile: str) -> list[str]:
    return [command.strip() for line in instructions(dockerfile) if line.startswith("RUN ")
            for command in re.split(r"&&|\|\||;", line) if re.search(r"\bpip install\b", command)]


def test_the_ide_image_installs_the_sdk_and_its_dependencies_in_hash_checking_mode():
    text = ide_dockerfile()
    assert "COPY ide/sdk-requirements.txt /tmp/sdk-requirements.txt" in instructions(text)
    sdk = [command for command in pip_installs(text) if "kionga" in command]
    assert len(sdk) == 1, "one pip install must bring in the SDK and its dependencies"
    assert "--require-hashes" in sdk[0].split() and "-r /tmp/sdk-requirements.txt" in sdk[0]
    assert "--no-deps" not in sdk[0], (
        "with --require-hashes and no --no-deps, pip fails on any SDK dependency the lock misses")


def test_the_jupyter_image_installs_the_sdk_dependencies_in_hash_checking_mode():
    text = (ROOT / "jupyter" / "Dockerfile").read_text()
    assert "COPY jupyter/sdk-requirements.txt /tmp/sdk-requirements.txt" in instructions(text)
    installs = pip_installs(text)
    lock = [i for i, command in enumerate(installs) if "-r /tmp/sdk-requirements.txt" in command]
    assert len(lock) == 1 and "--require-hashes" in installs[lock[0]].split()
    sdk = [i for i, command in enumerate(installs) if '"/opt/src/sdk[agents,huggingface]"' in command]
    assert sdk and min(sdk) > lock[0], "the locked dependencies must be installed before the SDK source"
    release = [installs[i] for i in sdk if "--no-deps" in installs[i].split()]
    assert len(release) == 1, "the release build must install the SDK source with --no-deps"
    # The closure check: with no index pip can only use what the lock installed.
    assert any(command.split()[:4] == ["pip", "install", "--no-index", '"kionga[agents,huggingface]"']
               for command in installs), "the release build must prove the lock covers the SDK"
    run = next(line for line in instructions(text) if "-r /tmp/sdk-requirements.txt" in line)
    assert re.search(r'if \[ "\$PLATFORM_SOURCE" = release \]; then\s+pip install --no-cache-dir --no-deps', run)
    assert re.search(r"&&\s+pip check;", run), "the release build must fail on a broken dependency set"


def lock_script():
    spec = importlib.util.spec_from_file_location("lock_sdk_dependencies",
                                                  ROOT / "scripts" / "lock_sdk_dependencies.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_lock_script_reads_the_release_the_dockerfiles_pin():
    script = lock_script()
    assert script.sdk_version((ROOT / "jupyter" / "Dockerfile").read_text()) == pins()[0]
    with pytest.raises(SystemExit):
        script.sdk_version("ARG SDK_VERSION=main\n")


def test_the_lock_script_resolves_the_jupyter_lock_with_every_package_the_image_installs():
    script = lock_script()
    packages = script.image_packages((ROOT / "jupyter" / "Dockerfile").read_text())
    names = {re.split(r"[=<>!~\[ ]", spec)[0] for spec in packages}
    assert {"jupyterlab", "mlflow", "scikit-learn", "prefect", "jupyter-ai", "jupyter-server-proxy"} <= names
    assert "kionga" not in names and not any("/" in spec for spec in packages)
    assert script.image_packages(
        '# RUN pip install "commented==1"\nRUN pip install --no-cache-dir \\\n    "a>=1,<2" \\\n'
        '    "b[x]==2" \\\n && echo "c==3" && pip install "/opt/src/sdk[agents]" "kionga[agents]" "d"\n'
    ) == ["a>=1,<2", "b[x]==2", "d"]
