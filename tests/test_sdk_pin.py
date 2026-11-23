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


def test_the_pinned_sdk_has_the_command_line_kionga_apps_needs():
    image, _ = pins()
    assert version(image) >= FIRST_WITH_CLI, f"SDK v{image} has no kionga.cli; pin v0.3.2 or later"


def test_the_installed_sdk_provides_kionga_cli():
    # requirements-dev.txt installs the pinned release, so this checks the release itself.
    assert importlib.util.find_spec("kionga.cli") is not None
