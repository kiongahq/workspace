#!/bin/sh
set -e

# Jupyter login token. JupyterLab binds to every interface and gives whoever
# holds the token a terminal, so startup fails closed: no token, the old
# built-in default or a token shorter than 32 characters stops the container.
# KIONGA_ALLOW_INSECURE_LOCAL=true accepts a weak or empty token for a
# single-user machine and then binds to 127.0.0.1 only.
jupyter_token="${JUPYTER_TOKEN:-}"
jupyter_ip="${KIONGA_JUPYTER_IP:-0.0.0.0}"
if [ "${KIONGA_ALLOW_INSECURE_LOCAL:-false}" = "true" ]; then
  echo "KIONGA_ALLOW_INSECURE_LOCAL=true: accepting any JUPYTER_TOKEN and binding JupyterLab to 127.0.0.1 only." >&2
  jupyter_ip=127.0.0.1
elif [ -z "$jupyter_token" ]; then
  echo "JUPYTER_TOKEN is not set. Set it to a random value of at least 32 characters (for example: openssl rand -hex 24)." >&2
  exit 1
elif [ "$jupyter_token" = "mlaiops-local" ] || [ "${#jupyter_token}" -lt 32 ]; then
  echo "JUPYTER_TOKEN is too weak: use a random value of at least 32 characters, not a shared default." >&2
  exit 1
fi
# The platform gateway is the only ingress and sets X-Forwarded-* headers.
# Set KIONGA_JUPYTER_TRUST_XHEADERS=false when anything else can reach port 8888.
case "${KIONGA_JUPYTER_TRUST_XHEADERS:-true}" in
  true) trust_xheaders=True ;;
  false) trust_xheaders=False ;;
  *) echo "KIONGA_JUPYTER_TRUST_XHEADERS must be true or false." >&2; exit 1 ;;
esac

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
# Each bucket is mounted at this workspace's own prefix (bucket:/prefix), never
# whole: the credentials are expected to reach that prefix only. Leading and
# trailing slashes are ignored.
mount_prefix="${S3_MOUNT_PREFIX:-}"
while [ "${mount_prefix#/}" != "$mount_prefix" ]; do mount_prefix="${mount_prefix#/}"; done
while [ "${mount_prefix%/}" != "$mount_prefix" ]; do mount_prefix="${mount_prefix%/}"; done

skip_mounts() {
  echo "$1" >&2
  if [ "${S3_MOUNT_OPTIONAL:-false}" != "true" ]; then
    exit 1
  fi
  echo "Continuing with the persistent /workspace volume; object storage remains available through the platform API." >&2
}

fuse_device="${KIONGA_FUSE_DEVICE:-/dev/fuse}"
if [ -z "${S3_ENDPOINT:-}" ] || [ ! -e "$fuse_device" ]; then
  skip_mounts "Object-store filesystem mount requires S3_ENDPOINT and /dev/fuse"
elif [ -z "$mount_prefix" ]; then
  skip_mounts "Object-store filesystem mount requires S3_MOUNT_PREFIX, this workspace's own prefix in each bucket (for example projects/<namespace>); refusing to mount whole buckets."
else
  case "$mount_prefix" in
    *[!A-Za-z0-9._/-]* | . | .. | ./* | ../* | */. | */.. | */./* | */../* | *//*)
      echo "S3_MOUNT_PREFIX may contain only letters, digits, '.', '_', '-' and '/' separators, with no '.' or '..' segments." >&2
      exit 1 ;;
  esac
  credentials="${KIONGA_S3FS_PASSWD_FILE:-/run/s3fs-passwd}"
  printf '%s:%s\n' "${AWS_ACCESS_KEY_ID}" "${AWS_SECRET_ACCESS_KEY}" > "$credentials"
  chmod 600 "$credentials"
  # Files belong to the workspace user (uid 1000) with mode 0700/0600 and the
  # kernel enforces it. Root mounts on dev's behalf, which needs allow_other.
  if [ "$(id -u)" = 0 ]; then
    access="-o allow_other"
  else
    access=""
  fi
  mkdir -p "$mount_root"
  for bucket in $mount_buckets; do
    target="$mount_root/$bucket"
    mkdir -p "$target"
    if ! mountpoint -q "$target"; then
      # shellcheck disable=SC2086 # $access is zero or two words on purpose
      s3fs "$bucket:/$mount_prefix" "$target" \
        -o "url=${S3_ENDPOINT}" \
        -o use_path_request_style \
        -o "passwd_file=${credentials}" \
        $access \
        -o default_permissions \
        -o uid=1000 \
        -o gid=1000 \
        -o umask=0077
    fi
  done
  chown dev:dev "$mount_root"
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
  --ip="$jupyter_ip" \
  --port=8888 \
  --no-browser \
  --ServerApp.root_dir=/workspace \
  --ServerApp.base_url=/workspaces/workbench/ \
  --ServerApp.trust_xheaders="$trust_xheaders" \
  --ArbitraryFileIdManager.db_path=/workspace/.jupyter/file_id_manager.db \
  --LabApp.extension_manager=readonly \
  --IdentityProvider.token="$jupyter_token"
