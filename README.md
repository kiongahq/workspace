# workspace

The developer workspaces of [Kionga](https://github.com/kiongahq): a shared Jupyter
workbench, a browser IDE, and the `kionga` workspace CLI they both carry.

| Path | Image | What it is |
| --- | --- | --- |
| `jupyter/` | `ghcr.io/kiongahq/jupyter` | JupyterLab with Jupyter AI, the Kionga SDK and platform modules (agents, features, realtime, pipelines), S3FS-mounted buckets, and Codex / Claude Code CLIs |
| `ide/` | `ghcr.io/kiongahq/ide` | code-server mounting the same `/workspace`; coding-agent CLIs are opt-in (`INSTALL_CODING_AGENTS=true`) |
| `workspace/kionga.py` | both | `kionga` CLI: project templates from one versioned catalog, generated deterministically; no credentials are read or written |
| `workspace/directories.py` | both | Loopback sidecar for project folders, structured scaffold jobs, and authenticated workspace-to-gateway API calls |

Both images serve under a path prefix the [platform](https://github.com/kiongahq/platform)
gateway proxies (`/workspaces/workbench/` for Jupyter); the gateway probes that path to
report readiness, and the [deploy](https://github.com/kiongahq/deploy) tests check the
two sides agree.

## Build

The workbench bundles code from three other repositories. By default it downloads
their tagged releases (versions are build args in `jupyter/Dockerfile`); for changes
that span repositories, use sibling checkouts:

```bash
docker build -f jupyter/Dockerfile -t ghcr.io/kiongahq/jupyter .          # releases
docker build -f jupyter/Dockerfile --build-arg PLATFORM_SOURCE=local \
  --build-context sdk=../sdk-python \
  --build-context agent-runtime=../agent-runtime \
  --build-context pipeline-runner=../pipeline-runner \
  -t ghcr.io/kiongahq/jupyter:dev .                                          # checkouts
docker build -f ide/Dockerfile -t ghcr.io/kiongahq/ide .
```

`jupyter/platform_sources.py` does the fetching; it refuses non-tag versions, unsafe
archive members, and mixing local with release sources.

## Develop

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt     # includes CPU PyTorch for the generated-project tests
python -m pytest -q && ruff check .
```

The CLI tests generate every template and run each generated project's own tests,
so a template that does not work out of the box fails here.
