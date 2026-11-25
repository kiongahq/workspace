# Jupyter workbench: notebooks + a browser terminal wired into the platform.
#
#   docker build -f jupyter/Dockerfile -t ghcr.io/kiongahq/jupyter .     # tagged releases
#   docker build -f jupyter/Dockerfile --build-arg PLATFORM_SOURCE=local \
#     --build-context sdk=../sdk-python \
#     --build-context agent-runtime=../agent-runtime \
#     --build-context pipeline-runner=../pipeline-runner -t ...:dev .   # sibling checkouts
#
# ML library versions are pinned to the model server image (mlflow/Dockerfile
# in kiongahq/deploy: mlflow 3.17.2, scikit-learn 1.7.0) so models trained in a
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

# Every Python package of the image except the SDK source (fetched below) comes
# from jupyter/image-requirements.txt,
# hash-locked and resolved together with the pinned SDK release by
# `python scripts/lock_sdk_dependencies.py`. The list below names what the image
# needs; the --no-index install can only use what the lock installed, so it fails
# the build if the lock no longer satisfies one of them. Copying the lock makes it
# part of the layer cache key: a new lock never reuses an older install.
# jupyter-server-proxy exposes the loopback workspace sidecar at
# /workspaces/workbench/proxy/8890 behind the notebook token, the same way
# code-server's /proxy/8890 does for the IDE (structured scaffold jobs).
COPY jupyter/image-requirements.txt /tmp/image-requirements.txt
RUN pip install --no-cache-dir --require-hashes -r /tmp/image-requirements.txt \
 && pip install --no-index --no-deps \
    "jupyterlab>=4.2,<5" \
    "scikit-learn==1.7.0" \
    "mlflow==3.17.2" \
    "pandas>=2.2" \
    "pyarrow>=16" \
    "boto3>=1.34" \
    "prefect>=3.0" \
    "redis>=5" \
    "jupyter-ai==3.0.1" \
    "jupyter-server-proxy==4.4.0" \
 && rm /tmp/image-requirements.txt

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
# The SDK's dependencies (its agents and huggingface extras included) come from
# jupyter/sdk-requirements.txt, which pins each one with its SHA-256; --require-hashes
# makes pip refuse anything without a matching hash. A release build then installs
# the SDK source with --no-deps, and the --no-index install after it fails the build
# if the lock no longer covers everything the SDK asks for (it can only use what is
# already installed). `pip check` fails the build if a locked version breaks a package
# installed above. A local build installs the sibling checkout normally, so a
# dependency the checkout has added since the pinned release still resolves.
# After changing SDK_VERSION run `python scripts/lock_sdk_dependencies.py`.
ARG PLATFORM_SOURCE=release
ARG SDK_VERSION=v0.3.3
ARG AGENT_RUNTIME_VERSION=v0.2.0
ARG PIPELINE_RUNNER_VERSION=v0.2.0
COPY --from=sdk / /opt/src/sdk/
COPY --from=agent-runtime / /opt/src/agent-runtime/
COPY --from=pipeline-runner / /opt/src/pipeline-runner/
COPY jupyter/platform_sources.py /usr/local/lib/kionga_platform_sources.py
COPY jupyter/sdk-requirements.txt /tmp/sdk-requirements.txt
RUN SDK_VERSION="$SDK_VERSION" AGENT_RUNTIME_VERSION="$AGENT_RUNTIME_VERSION" \
    PIPELINE_RUNNER_VERSION="$PIPELINE_RUNNER_VERSION" \
    python /usr/local/lib/kionga_platform_sources.py "$PLATFORM_SOURCE" /opt/src \
 && pip install --no-cache-dir --require-hashes -r /tmp/sdk-requirements.txt \
 && if [ "$PLATFORM_SOURCE" = release ]; then \
      pip install --no-cache-dir --no-deps "/opt/src/sdk[agents,huggingface]" \
      && pip install --no-index "kionga[agents,huggingface]" \
      && pip check; \
    else \
      pip install --no-cache-dir "/opt/src/sdk[agents,huggingface]"; \
    fi \
 && rm /tmp/sdk-requirements.txt \
 && mkdir -p /opt/platform/python \
 && cp -R /opt/src/agent-runtime/agents /opt/src/agent-runtime/features \
          /opt/src/agent-runtime/realtime /opt/src/pipeline-runner/pipelines \
          /opt/platform/python/ \
 && rm -rf /opt/src

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
