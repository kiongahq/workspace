"""The SDK the images and the tests pin must carry the command line that
`kionga apps` is passed on to (workspace/kionga.py hands it to kionga.cli)."""
import importlib.util
import re
from pathlib import Path

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
