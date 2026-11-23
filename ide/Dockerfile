FROM codercom/code-server:4.99.4

USER root
ARG TARGETARCH
ARG NODE_VERSION=22.17.0
ARG INSTALL_CODING_AGENTS=false
# Node.js publishes amd64 as "x64"; Docker's TARGETARCH is "amd64". Map it, or
# the tarball URL 404s on amd64 (the usual deployment architecture).
RUN apt-get update \
 && apt-get install -y --no-install-recommends git python3 python3-pip \
 && rm -rf /var/lib/apt/lists/*

# The editor must start without a second large registry/toolchain download.
# Opt in to agent CLIs with `make ide-agents-up` when those registries are reachable.
RUN if [ "$INSTALL_CODING_AGENTS" = true ]; then \
      apt-get update \
      && apt-get install -y --no-install-recommends curl xz-utils \
      && node_arch="$(case "${TARGETARCH}" in amd64) echo x64;; arm64) echo arm64;; *) echo "${TARGETARCH}";; esac)" \
      && curl -fsSL --retry 3 "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-${node_arch}.tar.xz" \
        | tar -xJ --strip-components=1 -C /usr/local \
      && npm install -g @openai/codex@0.142.5 @anthropic-ai/claude-code@2.1.200 \
      && rm -rf /var/lib/apt/lists/* /root/.npm; \
    fi

# The Kionga Python SDK, so `kionga apps` and `import kionga` work in the terminal.
# Only the core package: httpx and pydantic and what they pull in (about 15 MB). The
# agents and huggingface extras Jupyter carries would add dozens of packages and
# several hundred MB, and generated projects install what they need themselves.
# The wheel is the one the SDK's release workflow built and attached to the GitHub
# release, installed by SHA-256 so a moved tag or a swapped asset fails the build.
# Bookworm's Python is 3.11, the SDK's minimum. System site, like the Jupyter image.
# Bookworm marks its Python as externally managed (PEP 668), so a user installs
# packages in a virtual environment, or with `pip install --user --break-system-packages`
# into PYTHONUSERBASE, which then wins over this copy. The SDK's own dependencies
# (httpx, pydantic) resolve to the newest compatible releases at build time, as in the
# Jupyter image; only the SDK wheel is hash-pinned. To move to a new release, change both
# ARGs together: the digest is on the release page (SHA256SUMS) and tests/test_sdk_pin.py
# keeps SDK_VERSION equal to the Jupyter image and the test requirements.
ARG SDK_VERSION=v0.3.2
ARG SDK_WHEEL_SHA256=06ffdb0b7e642c802917894dd50aec2a050f900c910d44abed73c4dfb1bc3b70
RUN python3 -m pip install --no-cache-dir --break-system-packages \
    "kionga @ https://github.com/kiongahq/sdk-python/releases/download/${SDK_VERSION}/kionga-${SDK_VERSION#v}-py3-none-any.whl#sha256=${SDK_WHEEL_SHA256}"

COPY workspace/kionga.py /usr/local/bin/kionga
COPY workspace/directories.py /usr/local/lib/kionga_workspace_directories.py
COPY ide/entrypoint.sh /usr/local/bin/ide-workspace
RUN chmod 0755 /usr/local/bin/kionga /usr/local/bin/ide-workspace \
 && mkdir -p /workspace \
 && chown -R coder:coder /workspace
# Fails the build if the workspace command can no longer hand `kionga apps` to the SDK.
RUN kionga apps --help > /dev/null

WORKDIR /workspace
ENTRYPOINT ["dumb-init", "--", "ide-workspace"]
