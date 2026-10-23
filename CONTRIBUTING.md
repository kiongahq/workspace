# Contributing to workspace

Thank you for helping improve Kionga. Read [ARCHITECTURE.md](ARCHITECTURE.md) for
how the images, the CLI and the sidecar fit together before you make a larger
change.

## Development setup

Prerequisites:

- Python 3.11, the version of the Jupyter image and of CI
- Docker with BuildKit, to build the images
- Go, any recent stable release, only to run the gitleaks secret scan locally

```bash
git clone git@github.com:kiongahq/workspace.git
cd workspace
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
```

`requirements-dev.txt` installs the SDK release with its `runtime` and `dev` extras,
scikit-learn and CPU-only PyTorch, because the CLI tests run the projects they
generate. For a sibling SDK checkout instead:
`pip install -e "../sdk-python[runtime,dev]"`.

## Run the checks

CI calls the shared Python workflow
([`kiongahq/.github/.github/workflows/python.yml`](https://github.com/kiongahq/.github/blob/main/.github/workflows/python.yml))
with `pip install -r requirements-dev.txt`. Run the same steps locally:

```bash
ruff check .
python -m pytest -q
```

Then the security gates, with the versions CI pins:

```bash
pip install --upgrade pip setuptools "pip-audit==2.10.1"
pip-audit --skip-editable                                    # known vulnerabilities in installed packages
pip install "bandit==1.9.4"
bandit -q -r . -x ./tests,./.venv,./node_modules -ll         # medium and higher static findings
go run github.com/zricethezav/gitleaks/v8@v8.30.1 git --no-banner --redact .   # secrets in the full history
```

`tests/test_workspace_cli.py` generates every template and runs each generated
project's own test suite, so a template that does not work out of the box fails
here. Expect this suite to take longer than the others.

## Build the images

The Jupyter image bundles code from three other repositories: the SDK, the
`agents`, `features` and `realtime` packages of agent-runtime, and the `pipelines`
package of pipeline-runner. By default it downloads their tagged releases; the
versions are build arguments in `jupyter/Dockerfile` (`SDK_VERSION`,
`AGENT_RUNTIME_VERSION`, `PIPELINE_RUNNER_VERSION`).

```bash
# Tagged releases, as CI builds it
docker build -f jupyter/Dockerfile -t ghcr.io/kiongahq/jupyter:dev .

# Sibling checkouts, for a change that spans repositories
docker build -f jupyter/Dockerfile --build-arg PLATFORM_SOURCE=local \
  --build-context sdk=../sdk-python \
  --build-context agent-runtime=../agent-runtime \
  --build-context pipeline-runner=../pipeline-runner \
  -t ghcr.io/kiongahq/jupyter:dev .

# Browser IDE; add --build-arg INSTALL_CODING_AGENTS=true for the agent CLIs
docker build -f ide/Dockerfile -t ghcr.io/kiongahq/ide:dev .
```

After CI passes on pushes to `main` and on `v*` tags, the shared image workflow
publishes `ghcr.io/kiongahq/jupyter` and `ghcr.io/kiongahq/ide`, tagged
`sha-<short>`, `latest` (from `main`) and the semantic version (from tags). Pull
requests build both images without publishing them.

## Version alignment

MLflow and scikit-learn in `jupyter/Dockerfile` match the model server image
(`deploy/mlflow/Dockerfile`) and `pipeline-runner/requirements.txt`, so a model
trained in a notebook loads where it is served. Change all three together. When
the SDK, agent-runtime or pipeline-runner publish a release you need, bump the
matching build argument and the SDK pin in `requirements-dev.txt`.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/), as the history
does: `type(scope): summary` in the imperative mood, for example
`feat(workspace): persist user tools and proxy workspace identity` or
`fix(security): Jupyter image on MLflow 3.16.1`. Common types are `feat`, `fix`,
`docs`, `test`, `ci` and `chore`.

## Pull requests

- Keep one logical change per pull request, with tests for new behavior.
- CI must pass. Do not skip hooks or checks.
- The template catalog is a contract shared with the platform
  (`go/pkg/api/project_templates.go` in
  [platform](https://github.com/kiongahq/platform)). Change both sides together and
  link the platform pull request.
- A change to the sidecar's allowed scaffold flags needs a security review in the
  pull request description.

## Reviewed scanner findings

When bandit flags code that you have reviewed and found safe, annotate the line.
Put the reason in a comment on the line before it, and end the flagged line with
`# nosec <rule>` and nothing after it (bandit reads any text after `nosec` as rule
IDs):

```python
# KIONGA_URL is the control plane the user configured.
with urllib.request.urlopen(request, timeout=15) as response:  # nosec B310
```

If a test needs a fake credential that gitleaks reports, add the finding's
fingerprint (`commit:file:rule:line`, printed by gitleaks) to a `.gitleaksignore`
file at the repository root, with a comment that says why. A fingerprint pins one
exact finding, so any new secret still fails the scan.

## License

By contributing, you agree that your contributions are licensed under the
[MIT License](LICENCE).
