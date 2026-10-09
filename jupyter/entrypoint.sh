#!/bin/sh
set -e

jupyter_state=/workspace/.kionga/jupyter
export PYTHONUSERBASE="$jupyter_state/python-user"
export JUPYTER_CONFIG_DIR="$jupyter_state/config"
export JUPYTER_DATA_DIR="$jupyter_state/data"
export JUPYTERLAB_SETTINGS_DIR="$jupyter_state/lab-settings"
export JUPYTERLAB_WORKSPACES_DIR="$jupyter_state/lab-workspaces"
export NPM_CONFIG_PREFIX="$jupyter_state/npm"
export PATH="$PYTHONUSERBASE/bin:$NPM_CONFIG_PREFIX/bin:$PATH"
mkdir -p /home/dev/.codex /home/dev/.claude /workspace/.jupyter \
  "$PYTHONUSERBASE" "$JUPYTER_CONFIG_DIR" "$JUPYTER_DATA_DIR" \
  "$JUPYTERLAB_SETTINGS_DIR" "$JUPYTERLAB_WORKSPACES_DIR" "$NPM_CONFIG_PREFIX"
if [ "$(id -u)" = 0 ]; then
  chown dev:dev /workspace
  chown -R dev:dev /home/dev/.codex /home/dev/.claude /workspace/.jupyter "$jupyter_state"
  set -- runuser -u dev --
else
  set --
fi

mount_root="${S3_MOUNT_ROOT:-/workspace/object-store}"
mount_buckets="${S3_MOUNT_BUCKETS:-mlaiops-models mlaiops-artifacts mlaiops-features mlaiops-traces mlaiops-agents mlaiops-pipeline-logs}"

if [ -n "${S3_ENDPOINT:-}" ] && [ -e /dev/fuse ]; then
  credentials=/run/s3fs-passwd
  printf '%s:%s\n' "${AWS_ACCESS_KEY_ID}" "${AWS_SECRET_ACCESS_KEY}" > "$credentials"
  chmod 600 "$credentials"
  mkdir -p "$mount_root"
  for bucket in $mount_buckets; do
    target="$mount_root/$bucket"
    mkdir -p "$target"
    if ! mountpoint -q "$target"; then
      s3fs "$bucket" "$target" \
        -o "url=${S3_ENDPOINT}" \
        -o use_path_request_style \
        -o "passwd_file=${credentials}" \
        -o allow_other \
        -o uid=1000 \
        -o gid=1000 \
        -o umask=0022
    fi
  done
  chown dev:dev "$mount_root"
else
  echo "Object-store filesystem mount requires S3_ENDPOINT and /dev/fuse" >&2
  if [ "${S3_MOUNT_OPTIONAL:-false}" != "true" ]; then
    exit 1
  fi
  echo "Continuing with the persistent /workspace volume; object storage remains available through the platform API." >&2
fi

# Seed the quickstart once; everything under /workspace persists in the
# jupyter-data volume, so user edits are never overwritten.
if [ ! -f /workspace/quickstart.ipynb ]; then
  cp /opt/seed/quickstart.ipynb /workspace/quickstart.ipynb
fi

# Loopback-only workspace sidecar (project folders and structured scaffold
# jobs). Jupyter reaches it through jupyter-server-proxy behind its token.
"$@" env KIONGA_WORKSPACE=/workspace python3 /usr/local/lib/kionga_workspace_directories.py &

exec "$@" jupyter lab \
  --ip=0.0.0.0 \
  --port=8888 \
  --no-browser \
  --ServerApp.root_dir=/workspace \
  --ServerApp.base_url=/workspaces/workbench/ \
  --ServerApp.trust_xheaders=True \
  --ArbitraryFileIdManager.db_path=/workspace/.jupyter/file_id_manager.db \
  --LabApp.extension_manager=readonly \
  --IdentityProvider.token="${JUPYTER_TOKEN:-mlaiops-local}"
