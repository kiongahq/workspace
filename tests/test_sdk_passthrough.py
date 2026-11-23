"""The workspace `kionga` command hands commands it doesn't own to the SDK's CLI.

The images install this script as /usr/local/bin/kionga after the SDK, so without
the passthrough the SDK's `kionga apps` would be unreachable in a workspace.
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).parents[1] / "workspace" / "kionga.py"
SPEC = importlib.util.spec_from_file_location("kionga_workspace_passthrough", MODULE_PATH)
assert SPEC and SPEC.loader
kionga = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kionga)

# A stand-in SDK command line: records its arguments and the gateway address.
FAKE_CLI = textwrap.dedent('''
    import argparse
    import json
    import os


    def parser():
        root = argparse.ArgumentParser(prog="kionga")
        root.add_argument("--url")
        commands = root.add_subparsers(dest="command", required=True)
        commands.add_parser("apps")
        return root


    def main(argv=None):
        print(json.dumps({"argv": argv, "url": os.environ.get("KIONGA_URL")}))
        return 3
''')


@pytest.fixture
def fake_sdk(tmp_path):
    package = tmp_path / "sdk" / "kionga"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (package / "cli.py").write_text(FAKE_CLI)
    return tmp_path / "sdk"


def run(script, *args, sdk=None, env=None):
    environment = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    environment.pop("KIONGA_URL", None)
    if sdk:
        environment["PYTHONPATH"] = str(sdk)
    environment.update(env or {})
    return subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True,
                          env=environment, timeout=60, check=False)


class FakeCli:
    def __init__(self, commands=("apps",), code=0):
        self.commands, self.code, self.calls = commands, code, []

    def parser(self):
        import argparse

        root = argparse.ArgumentParser(prog="kionga")
        sub = root.add_subparsers(dest="command")
        for name in self.commands:
            sub.add_parser(name)
        return root

    def main(self, argv):
        self.calls.append(argv)
        return self.code


@pytest.mark.parametrize("argv, command", [
    (["apps", "list"], "apps"),
    (["--url", "http://g", "apps", "list"], "apps"),
    (["--url=http://g", "apps"], "apps"),
    (["-h"], None),
    ([], None),
    (["scaffold", "x"], "scaffold"),
])
def test_requested_command_skips_options_and_their_values(argv, command):
    assert kionga.requested_command(argv) == command


def test_sdk_commands_are_handed_to_the_sdk_with_every_argument(monkeypatch):
    cli = FakeCli(code=4)
    monkeypatch.setattr(kionga, "load_sdk_cli", lambda: cli)
    assert kionga.main(["--url", "http://g", "apps", "list", "--json"]) == 4
    assert cli.calls == [["--url", "http://g", "apps", "list", "--json"]]


def test_workspace_commands_stay_here_even_when_the_sdk_has_one_of_the_same_name(monkeypatch, capsys):
    cli = FakeCli(commands=("apps", "templates"))
    monkeypatch.setattr(kionga, "load_sdk_cli", lambda: cli)
    assert kionga.main(["templates"]) == 0
    assert cli.calls == []
    assert "production-ml" in capsys.readouterr().out


def test_a_missing_or_old_sdk_explains_how_to_get_the_command(monkeypatch, capsys):
    monkeypatch.setattr(kionga, "load_sdk_cli", lambda: None)
    assert kionga.main(["apps", "list"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("kionga: `kionga apps` comes from the Kionga Python SDK")
    assert "pip install kionga" in err


def test_an_unknown_command_with_the_sdk_present_gets_the_usual_usage_error(monkeypatch, capsys):
    monkeypatch.setattr(kionga, "load_sdk_cli", lambda: FakeCli())
    with pytest.raises(SystemExit) as caught:
        kionga.main(["scafold"])
    assert caught.value.code == 2
    assert "invalid choice: 'scafold'" in capsys.readouterr().err


def test_help_lists_the_sdk_commands(monkeypatch, capsys):
    monkeypatch.setattr(kionga, "load_sdk_cli", lambda: FakeCli())
    with pytest.raises(SystemExit):
        kionga.main(["--help"])
    assert "Kionga SDK commands: apps." in capsys.readouterr().out


def test_workspace_errors_still_exit_1_with_the_kionga_prefix(monkeypatch, capsys):
    monkeypatch.setattr(kionga, "load_sdk_cli", lambda: None)
    monkeypatch.setattr(kionga, "api_get", lambda path: (_ for _ in ()).throw(RuntimeError("control plane is unavailable")))
    assert kionga.main(["project", "sync", "p-1"]) == 1
    assert capsys.readouterr().err == "kionga: control plane is unavailable\n"


def test_the_checkout_script_finds_the_installed_sdk_not_itself(fake_sdk):
    # workspace/kionga.py sits in the folder Python puts first on the path.
    result = run(MODULE_PATH, "apps", "list", sdk=fake_sdk)
    assert result.returncode == 3, result.stderr
    assert '"argv": ["apps", "list"]' in result.stdout


def test_the_installed_script_passes_through_and_shares_the_gateway_address(tmp_path, fake_sdk):
    # The images copy the script to /usr/local/bin/kionga, without an extension.
    script = tmp_path / "bin" / "kionga"
    script.parent.mkdir()
    shutil.copy(MODULE_PATH, script)
    result = run(script, "apps", "get", "billing", sdk=fake_sdk)
    assert result.returncode == 3, result.stderr
    assert '"url": "http://gateway:8080"' in result.stdout, "the workspace default reaches the SDK"
    result = run(script, "apps", sdk=fake_sdk, env={"KIONGA_URL": "http://127.0.0.1:8890"})
    assert '"url": "http://127.0.0.1:8890"' in result.stdout, "a configured address is kept"


def test_the_installed_script_without_the_sdk_cli_says_so(tmp_path):
    empty = tmp_path / "empty"
    (empty / "kionga").mkdir(parents=True)
    (empty / "kionga" / "__init__.py").write_text("")  # an SDK release without kionga.cli
    result = run(MODULE_PATH, "apps", "list", sdk=empty)
    assert result.returncode == 1
    assert "comes from the Kionga Python SDK" in result.stderr


@pytest.mark.parametrize("argv", [["--url", "http://g", "--help"], ["--url=http://g"]])
def test_sdk_root_options_without_a_command_go_to_the_sdk(monkeypatch, argv):
    cli = FakeCli(code=0)
    monkeypatch.setattr(kionga, "load_sdk_cli", lambda: cli)
    assert kionga.main(argv) == 0
    assert cli.calls == [argv]


def test_sdk_root_options_without_the_sdk_say_how_to_get_it(monkeypatch, capsys):
    monkeypatch.setattr(kionga, "load_sdk_cli", lambda: None)
    assert kionga.main(["--url", "http://g", "--help"]) == 1
    assert "comes from the Kionga Python SDK" in capsys.readouterr().err


def test_plain_help_stays_with_the_workspace_command(monkeypatch, capsys):
    cli = FakeCli()
    monkeypatch.setattr(kionga, "load_sdk_cli", lambda: cli)
    with pytest.raises(SystemExit) as caught:
        kionga.main(["--help"])
    assert caught.value.code == 0 and cli.calls == []
    assert "Kionga AI workspace tools" in capsys.readouterr().out
