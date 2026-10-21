# Jupyter workbench: notebooks + a browser terminal wired into the platform.
#
#   docker build -f jupyter/Dockerfile -t ghcr.io/kiongahq/jupyter .     # tagged releases
#   docker build -f jupyter/Dockerfile --build-arg PLATFORM_SOURCE=local \
#     --build-context sdk=../sdk-python \
#     --build-context agent-runtime=../agent-runtime \
#     --build-context pipeline-runner=../pipeline-runner -t ...:dev .   # sibling checkouts
#
# ML library versions are pinned to the model server image (mlflow/Dockerfile
# in kiongahq/deploy: mlflow 3.16.1, scikit-learn 1.7.0) so models trained in a
# notebook load under `mlflow models serve` without training-serving skew.

# Empty unless overridden with --build-context <name>=<dir>.
FROM scratch AS sdk
FROM scratch AS agent-runtime
FROM scratch AS pipeline-runner

FROM python:3.11-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends git curl fuse3 s3fs \
 && printf 'user_allow_other\n' >> /etc/fuse.conf \
 && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    "jupyterlab>=4.2,<5" \
    "scikit-learn==1.7.0" \
    "mlflow==3.16.1" \
    "pandas>=2.2" \
    "pyarrow>=16" \
    "boto3>=1.34" \
    "prefect>=3.0" \
    "redis>=5"

ARG TARGETARCH
ARG NODE_VERSION=22.17.0
# Node.js publishes amd64 as "x64"; Docker's TARGETARCH is "amd64". Map it, or
# the tarball URL 404s on amd64 (the usual deployment architecture).
RUN apt-get update \
 && apt-get install -y --no-install-recommends xz-utils \
 && node_arch="$(case "${TARGETARCH}" in amd64) echo x64;; arm64) echo arm64;; *) echo "${TARGETARCH}";; esac)" \
 && curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-${node_arch}.tar.xz" \
    | tar -xJ --strip-components=1 -C /usr/local \
 && npm install -g @openai/codex@0.142.5 @anthropic-ai/claude-code@2.1.200 \
 && rm -rf /var/lib/apt/lists/* /root/.npm

# The platform SDK and the runnable platform modules (features, realtime,
# pipelines, agents) so notebooks and the terminal can drive the whole stack.
# PLATFORM_SOURCE is explicit so it is part of the layer cache key: a release
# build never reuses a layer built from local checkouts.
ARG PLATFORM_SOURCE=release
ARG SDK_VERSION=v0.2.0
ARG AGENT_RUNTIME_VERSION=v0.1.0
ARG PIPELINE_RUNNER_VERSION=v0.1.0
COPY --from=sdk / /opt/src/sdk/
COPY --from=agent-runtime / /opt/src/agent-runtime/
COPY --from=pipeline-runner / /opt/src/pipeline-runner/
COPY jupyter/platform_sources.py /usr/local/lib/kionga_platform_sources.py
RUN SDK_VERSION="$SDK_VERSION" AGENT_RUNTIME_VERSION="$AGENT_RUNTIME_VERSION" \
    PIPELINE_RUNNER_VERSION="$PIPELINE_RUNNER_VERSION" \
    python /usr/local/lib/kionga_platform_sources.py "$PLATFORM_SOURCE" /opt/src \
 && pip install --no-cache-dir "/opt/src/sdk[agents,huggingface]" \
 && mkdir -p /opt/platform/python \
 && cp -R /opt/src/agent-runtime/agents /opt/src/agent-runtime/features \
          /opt/src/agent-runtime/realtime /opt/src/pipeline-runner/pipelines \
          /opt/platform/python/ \
 && rm -rf /opt/src
RUN pip install --no-cache-dir "jupyter-ai==3.0.1"
# jupyter-server-proxy exposes the loopback workspace sidecar at
# /workspaces/workbench/proxy/8890 behind the notebook token, the same way
# code-server's /proxy/8890 does for the IDE (structured scaffold jobs).
RUN pip install --no-cache-dir "jupyter-server-proxy==4.4.0"

COPY jupyter/quickstart.ipynb /opt/seed/quickstart.ipynb
COPY jupyter/entrypoint.sh /usr/local/bin/workbench
COPY workspace/kionga.py /usr/local/bin/kionga
COPY workspace/directories.py /usr/local/lib/kionga_workspace_directories.py
RUN chmod +x /usr/local/bin/workbench \
 && chmod +x /usr/local/bin/kionga \
 && useradd --create-home --uid 1000 dev \
 && mkdir -p /workspace /workspace/object-store \
 && chown -R dev:dev /workspace

ENV PYTHONPATH=/opt/platform/python \
    SHELL=/bin/bash

WORKDIR /workspace
EXPOSE 8888
ENTRYPOINT ["workbench"]
