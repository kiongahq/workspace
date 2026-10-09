#!/bin/sh
set -eu

ide_state=/workspace/.kionga/ide
export XDG_DATA_HOME="$ide_state/data"
export XDG_CONFIG_HOME="$ide_state/config"
export PYTHONUSERBASE="$ide_state/python-user"
export NPM_CONFIG_PREFIX="$ide_state/npm"
export PATH="$PYTHONUSERBASE/bin:$NPM_CONFIG_PREFIX/bin:$PATH"
mkdir -p /home/coder/.codex /home/coder/.claude "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" \
  "$PYTHONUSERBASE" "$NPM_CONFIG_PREFIX"
if [ "$(id -u)" = 0 ]; then
  chown coder:coder /workspace
  chown -R coder:coder /home/coder/.codex /home/coder/.claude "$ide_state"
  set -- runuser -u coder --
else
  set --
fi

"$@" python3 /usr/local/lib/kionga_workspace_directories.py &

exec "$@" code-server \
  --bind-addr 0.0.0.0:8080 \
  --auth "${KIONGA_IDE_AUTH_MODE:-password}" \
  --user-data-dir "$XDG_DATA_HOME/code-server" \
  --extensions-dir "$XDG_DATA_HOME/code-server/extensions" \
  --abs-proxy-base-path=/workspaces/ide \
  /workspace
