# workspace

[![CI](https://github.com/kiongahq/workspace/actions/workflows/ci.yml/badge.svg)](https://github.com/kiongahq/workspace/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENCE)

Kionga's developer workspaces: the Jupyter workbench, the browser IDE and the `kionga` project CLI.

## Background

Kionga is a self-hosted platform for machine learning, data and AI agents. Each
person on a Kionga installation works in a personal workspace that the console
opens in the browser. This repository builds the two workspace images:

- `ghcr.io/kiongahq/jupyter`: JupyterLab with Jupyter AI, the Kionga Python SDK,
  the platform's runnable modules (agents, features, real-time, pipelines) and the
  object store buckets mounted as folders.
- `ghcr.io/kiongahq/ide`: a browser IDE (code-server) on the same `/workspace`
  folder. Coding-agent CLIs are optional.

Both carry the `kionga` CLI, which generates production-shaped projects from a
versioned template catalog, and a small sidecar that lets the console create
project folders and lets the SDK reach the platform as the workspace owner.

## Install

```bash
git clone git@github.com:kiongahq/workspace.git
cd workspace
docker build -f jupyter/Dockerfile -t ghcr.io/kiongahq/jupyter:dev .
docker build -f ide/Dockerfile -t ghcr.io/kiongahq/ide:dev .
```

The [deploy](https://github.com/kiongahq/deploy) repository builds and runs both
images with the rest of Kionga.

## Usage

Inside a workspace, generate a project from a template:

```bash
kionga templates                                   # list the catalog
kionga scaffold churn --template production-ml     # creates /workspace/churn
kionga project sync <project-id>                   # clone or update a project's Git repository
```

Templates: `production-ml`, `distributed-training`, `production-agent`,
`fullstack-ai` and `blank-python`. Outside a workspace, run
`python workspace/kionga.py` with `KIONGA_WORKSPACE` set to the target folder.

## Documentation

- Product documentation: [Jupyter workbench](https://kiongahq.github.io/docs/guides/workbench/),
  [Browser IDE and coding agents](https://kiongahq.github.io/docs/guides/coding-workspace/)
  and [Scaffold a project](https://kiongahq.github.io/docs/guides/scaffolding/)
- Engineering handbook: <https://kiongahq.github.io/docs/engineering/>
- How this repository is laid out: [ARCHITECTURE.md](ARCHITECTURE.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development setup, the checks CI
runs and the commit conventions.

## License

[MIT](LICENCE) © Kionga contributors
