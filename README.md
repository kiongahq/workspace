# workspace

[![CI](https://github.com/kiongahq/workspace/actions/workflows/ci.yml/badge.svg)](https://github.com/kiongahq/workspace/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENCE)

Kionga's developer workspaces: the Jupyter workbench, browser IDE, Langflow canvas, and the `kionga` project CLI.

## Background

Kionga is a self-hosted platform for machine learning, data and AI agents. Each
person on a Kionga installation works in a personal workspace that the console
opens in the browser. This repository builds the workspace images:

- `ghcr.io/kiongahq/jupyter`: JupyterLab with Jupyter AI, the Kionga Python SDK,
  the platform's runnable modules (agents, features, real-time, pipelines) and the
  object store buckets mounted as folders.
- `ghcr.io/kiongahq/ide`: a browser IDE (code-server) on the same `/workspace`
  folder. Coding-agent CLIs are optional.
- `ghcr.io/kiongahq/langflow`: a project-scoped visual flow builder with Kionga
  model, function, storage, and tool components.
- `ghcr.io/kiongahq/langflow-sidecar`: a loopback API helper that holds the
  workspace credential outside the Langflow process.

Jupyter and the IDE carry the `kionga` CLI, which generates production-shaped projects from a
versioned template catalog, and a small sidecar that lets the console create
project folders and lets the SDK reach the platform as the workspace owner.

## Install

```bash
git clone git@github.com:kiongahq/workspace.git
cd workspace
docker build -f jupyter/Dockerfile -t ghcr.io/kiongahq/jupyter:dev .
docker build -f ide/Dockerfile -t ghcr.io/kiongahq/ide:dev .
docker build -f langflow/Dockerfile -t ghcr.io/kiongahq/langflow:dev .
docker build -f langflow/Dockerfile.sidecar -t ghcr.io/kiongahq/langflow-sidecar:dev .
```

The [deploy](https://github.com/kiongahq/deploy) repository builds and runs these
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

## Configuration

The deployment sets these in each workspace container:

| Variable | Image | Required | Purpose |
| --- | --- | --- | --- |
| `JUPYTER_TOKEN` | Jupyter | Yes | JupyterLab login token, at least 32 random characters. The gateway proxies with the same value (`KIONGA_JUPYTER_TOKEN`). The container exits at startup when it is unset, shorter, or the old `mlaiops-local` default. |
| `KIONGA_ALLOW_INSECURE_LOCAL` | Jupyter | No | `true` accepts a weak or empty `JUPYTER_TOKEN` on a single-user machine and binds JupyterLab to `127.0.0.1` only, so the platform gateway cannot reach it. Never set it on a shared host. |
| `KIONGA_JUPYTER_TRUST_XHEADERS` | Jupyter | No | Default `true`: JupyterLab trusts `X-Forwarded-*` headers because the platform gateway is the only ingress. Set `false` when anything else can reach port 8888. |
| `S3_MOUNT_PREFIX` | Jupyter | When mounting | This workspace's own prefix in every mounted bucket, for example `projects/<namespace>`. Each bucket in `S3_MOUNT_BUCKETS` is mounted as `bucket:/<prefix>`, never whole. With `S3_ENDPOINT` and `/dev/fuse` present, an unset prefix stops the container, unless `S3_MOUNT_OPTIONAL=true`, which skips the mounts. Letters, digits, `.`, `_`, `-` and `/` only, with no `.` or `..` segments. |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | Jupyter | When mounting | Object-store credentials for the mounts. Use per-workspace, ideally short-lived credentials limited to the prefix (see below). |
| `KIONGA_WORKSPACE_JOB_TOKEN` | Jupyter, IDE | For scaffold jobs | Random value of at least 32 bytes that the gateway sends with `POST /scaffold-jobs`. Unset or shorter values disable scaffold jobs (HTTP 503). It is separate from the login credentials: `JUPYTER_TOKEN` and `PASSWORD` never authorize jobs. |

### Object-store credentials

Mounted files belong to the workspace user (uid 1000) with modes 0700 and 0600,
and the kernel enforces them (`default_permissions`, `umask=0077`). The prefix
limits what the mount shows, not what the credentials can reach, so give each
workspace credentials that can reach only its own prefix. For an S3-compatible
store (AWS IAM, RustFS or MinIO policies), the shape is:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": ["arn:aws:s3:::mlaiops-models", "arn:aws:s3:::mlaiops-artifacts"],
      "Condition": {"StringLike": {"s3:prefix": ["projects/<namespace>", "projects/<namespace>/*"]}}
    },
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
      "Resource": ["arn:aws:s3:::mlaiops-models/projects/<namespace>/*",
                   "arn:aws:s3:::mlaiops-artifacts/projects/<namespace>/*"]
    }
  ]
}
```

List every bucket in `S3_MOUNT_BUCKETS`. Where the store supports it, issue them
as STS session credentials scoped by this policy.

## Documentation

- Product documentation: [Jupyter workbench](https://kiongahq.github.io/docs/guides/workbench/),
  [Browser IDE and coding agents](https://kiongahq.github.io/docs/guides/coding-workspace/)
  [Langflow canvas](https://kiongahq.github.io/docs/guides/langflow/)
  and [Scaffold a project](https://kiongahq.github.io/docs/guides/scaffolding/)
- Engineering handbook: <https://kiongahq.github.io/docs/engineering/>
- How this repository is laid out: [ARCHITECTURE.md](ARCHITECTURE.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development setup, the checks CI
runs and the commit conventions.

## License

[MIT](LICENCE) © Kionga contributors
