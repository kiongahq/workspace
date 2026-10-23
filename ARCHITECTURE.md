# Architecture

This document describes how the workspace images, the `kionga` CLI and the
workspace sidecar are organized, and how they connect to the Kionga gateway.

## Bird's-eye view

A Kionga workspace is a container that a person opens from the console. The
gateway reverse-proxies it under a path prefix and checks the person's session on
every request. This repository produces two such containers that share one
`/workspace` folder:

| Image | Built from | Serves |
| --- | --- | --- |
| `ghcr.io/kiongahq/jupyter` | `jupyter/Dockerfile` | JupyterLab on port `8888` at `/workspaces/workbench/` |
| `ghcr.io/kiongahq/ide` | `ide/Dockerfile` | code-server on port `8080` at `/workspaces/ide` |

Both images include two Python programs from `workspace/`: the `kionga` CLI
(`/usr/local/bin/kionga`) and the sidecar, which the entrypoint starts in the
background on loopback before the editor.

## Code map

### `workspace/kionga.py`

The `kionga` CLI, standard library only.

- `TEMPLATE_CATALOG` is the versioned template catalog (`production-ml`,
  `distributed-training`, `production-agent`, `fullstack-ai`, `blank-python`), with
  each template's frameworks, accelerators and recommended profile.
  `RESOURCE_PROFILES` (`starter`, `team`, `power`, `gpu`, `custom`) and
  `ACCELERATOR_RESOURCES` (`cpu`, `single-gpu`, `multi-gpu`) define the resources
  a generated project requests.
- `scaffold` generates a project under `KIONGA_WORKSPACE` (default `/workspace`).
  Generation is deterministic and never reads or writes credentials. Generated
  projects carry their own tests, Dockerfile and platform manifests.
- `templates` prints the catalog (`--json` for the machine form), `agents` reports
  which coding-agent CLIs are installed, and `project sync` clones or fast-forwards
  a project's connected Git repository through the gateway API.

### `workspace/directories.py`

The sidecar: a `ThreadingHTTPServer` on `127.0.0.1:8890` (`KIONGA_SIDECAR_PORT`),
reachable only through the editor's own authenticated port proxy (`/proxy/8890`).

- `POST /prepare-project` creates `/workspace/projects/<namespace>`.
- `POST /scaffold-jobs` runs `kionga scaffold` with an argument list that the
  gateway built. `validate_job` re-checks it against a fixed flag allowlist and a
  strict character class; `run_scaffold` runs it without a shell, with a scrubbed
  environment and a timeout (`KIONGA_SCAFFOLD_TIMEOUT`, default 60 seconds). The
  request must carry the shared job token.
- `/api/v1/*` forwards SDK and CLI calls to the gateway's internal workspace
  listener (`KIONGA_GATEWAY_INTERNAL_URL`) with the workspace's provisioned
  identity (`X-Kionga-Workspace-Name` and `X-Kionga-Workspace-Token`). It never
  forwards the caller's cookies or authorization headers and caps request and
  response sizes.

### `jupyter/`

- `Dockerfile`: Python 3.11 with JupyterLab 4, Jupyter AI, pinned MLflow and
  scikit-learn, s3fs, Node.js and the Codex and Claude Code CLIs. It installs the
  SDK and copies `agents`, `features`, `realtime` and `pipelines` into
  `/opt/platform/python` (on `PYTHONPATH`).
- `platform_sources.py`: fetches those sources, either as tagged GitHub release
  archives (`release`) or from BuildKit named contexts (`local`). It refuses
  non-tag versions, unsafe archive members and a mix of the two modes.
- `entrypoint.sh`: keeps Jupyter settings, user-installed Python and npm tools
  under `/workspace/.kionga/jupyter` so they persist, mounts the object store
  buckets under `/workspace/object-store` with s3fs when `S3_ENDPOINT` and
  `/dev/fuse` are present, seeds `quickstart.ipynb` once, starts the sidecar and
  launches JupyterLab with `JUPYTER_TOKEN`.
- `quickstart.ipynb`: the seed notebook.

### `ide/`

- `Dockerfile`: `codercom/code-server:4.99.4` with the CLI and sidecar. Coding-agent
  CLIs install only with `INSTALL_CODING_AGENTS=true`.
- `entrypoint.sh`: keeps editor state and user tools under `/workspace/.kionga/ide`,
  starts the sidecar and launches code-server (`KIONGA_IDE_AUTH_MODE`, default
  `password`).

### `tests/`

`test_workspace_cli.py` checks the catalog, generates every template and runs each
generated project's tests. `test_workspace_directories.py` covers the sidecar's
validation and forwarding. `test_platform_sources.py` covers release and local
source bundling.

## Invariants

- **No credentials in generated code.** The scaffolder accepts and writes none.
- **The sidecar is loopback-only** and is reached through the editor's
  authenticated proxy. It never runs a shell, never accepts filesystem paths and
  never reads workspace files back.
- **Workspace identity comes from provisioning.** API calls from workspace code
  reach the gateway as the workspace owner; the gateway re-checks the owner's
  current access on every request.
- **User state persists.** Everything the person changes lives under `/workspace`,
  so recreating a container keeps notebooks, settings and installed tools.

## How it connects to other components

- **platform**: the gateway proxies `/workspaces/workbench/` and `/workspaces/ide`,
  probes them for readiness, builds scaffold jobs from stored projects, and
  accepts sidecar calls on its internal workspace listener (port `8087`). On
  Kubernetes, the operator runs one workspace pod per access grant with these
  images. The template catalog mirrors `go/pkg/api/project_templates.go` in the
  platform; no automated check compares the two, so change them together.
- **sdk-python, agent-runtime, pipeline-runner**: bundled into the Jupyter image at
  tagged releases.
- **deploy**: `compose.yaml` builds both images from this checkout (the IDE behind
  the `ide` profile), and its tests check that the gateway and the images agree on
  paths.

## Cross-cutting concerns

- **Version alignment.** MLflow and scikit-learn pins match the model server and
  the pipeline runner. See [CONTRIBUTING.md](CONTRIBUTING.md).
- **Security gates.** CI runs ruff, pytest, pip-audit, bandit and gitleaks through
  the shared Python workflow.
