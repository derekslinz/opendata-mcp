#!/usr/bin/env bash
# Install meta-data-mcp as a systemd-managed SSE server.
#
# Creates a service user, installs the package for that user via uv,
# generates a bearer token, writes /etc/meta-data-mcp/env and the
# systemd unit, and (optionally) starts the service.
#
# Usage (typical):
#   curl -fsSL https://raw.githubusercontent.com/derekslinz/meta-data-mcp/main/scripts/install-systemd-service.sh | sudo bash -s -- --start
#
# Local invocation:
#   sudo ./scripts/install-systemd-service.sh --start
#
# Re-running is safe: existing env file / unit are backed up to <file>.bak
# before being overwritten. Existing tokens are preserved unless --rotate-token
# is passed.

set -euo pipefail

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

SERVICE_NAME="meta-data-mcp"
SERVICE_USER="mcp"
HOST="127.0.0.1"
PORT="8000"
ENV_DIR="/etc/meta-data-mcp"
UNIT_DIR="/etc/systemd/system"
SOURCE_DIR=""              # if set, run from this source checkout via `uv --directory`
TOKEN=""                   # if set, use this token; else generate
ROTATE_TOKEN=0             # force-regenerate even if env file already has one
START=0                    # enable + start after install
DRY_RUN=0
UNINSTALL=0
CONTACT_EMAIL=""           # OPENDATA_MCP_CONTACT env var

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

log() { printf '%s\n' "$*"; }
err() { printf 'error: %s\n' "$*" >&2; }
die() { err "$@"; exit 1; }

run() {
  if [ "$DRY_RUN" -eq 1 ]; then
    log "    [dry-run] $*"
  else
    "$@"
  fi
}

usage() {
  cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Install meta-data-mcp as a systemd-managed SSE server with bearer-token auth.

Options:
  --user USER          Service user to create / run as (default: $SERVICE_USER)
  --host HOST          Bind address (default: $HOST)
  --port PORT          Bind port (default: $PORT)
  --token TOKEN        Use this bearer token instead of generating one
  --rotate-token       Generate a new token even if one already exists
  --contact EMAIL      Set OPENDATA_MCP_CONTACT (advised: most APIs require it)
  --source DIR         Run from a local source checkout (uv --directory DIR)
                       instead of \`uv tool install meta-data-mcp\` from PyPI
  --service-name NAME  systemd unit / env dir name (default: $SERVICE_NAME)
  --env-dir DIR        Directory for env file (default: $ENV_DIR)
  --start              Enable + start the service after install
  --uninstall          Stop, disable, and remove the unit + env file (keeps user)
  --dry-run            Show what would be done, do not change anything
  -h, --help           Print this help and exit

Examples:
  sudo $(basename "$0") --start --contact ops@yourdomain.example
  sudo $(basename "$0") --source /opt/meta-data-mcp --start
  sudo $(basename "$0") --rotate-token       # rotate token + restart
  sudo $(basename "$0") --uninstall
EOF
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

while [ $# -gt 0 ]; do
  case "$1" in
    --user)         SERVICE_USER="$2"; shift 2 ;;
    --host)         HOST="$2"; shift 2 ;;
    --port)         PORT="$2"; shift 2 ;;
    --token)        TOKEN="$2"; shift 2 ;;
    --rotate-token) ROTATE_TOKEN=1; shift ;;
    --contact)      CONTACT_EMAIL="$2"; shift 2 ;;
    --source)       SOURCE_DIR="$2"; shift 2 ;;
    --service-name) SERVICE_NAME="$2"; shift 2 ;;
    --env-dir)      ENV_DIR="$2"; shift 2 ;;
    --start)        START=1; shift ;;
    --uninstall)    UNINSTALL=1; shift ;;
    --dry-run)      DRY_RUN=1; shift ;;
    -h|--help)      usage; exit 0 ;;
    *)              die "unknown argument: $1 (try --help)" ;;
  esac
done

UNIT_FILE="$UNIT_DIR/${SERVICE_NAME}.service"
ENV_FILE="$ENV_DIR/env"

# ---------------------------------------------------------------------------
# Pre-flight
# ---------------------------------------------------------------------------

[ "$(uname -s)" = "Linux" ] || die "this script targets Linux + systemd; for macOS use launchd or run \`meta-data-mcp run --transport sse\` directly."
command -v systemctl >/dev/null || die "systemctl not found — this host doesn't appear to use systemd."

if [ "$(id -u)" -ne 0 ] && [ "$DRY_RUN" -eq 0 ]; then
  die "must be run as root (try: sudo $0 $*)"
fi

# ---------------------------------------------------------------------------
# Uninstall path
# ---------------------------------------------------------------------------

if [ "$UNINSTALL" -eq 1 ]; then
  log "Uninstalling $SERVICE_NAME"
  if systemctl list-unit-files | grep -q "^${SERVICE_NAME}.service"; then
    run systemctl stop "$SERVICE_NAME" || true
    run systemctl disable "$SERVICE_NAME" || true
  fi
  run rm -f "$UNIT_FILE"
  run systemctl daemon-reload
  if [ -f "$ENV_FILE" ]; then
    log "  keeping env file at $ENV_FILE (delete manually if no longer needed)"
  fi
  log "  service user '$SERVICE_USER' was not removed (delete manually if no longer needed)"
  log "Done."
  exit 0
fi

# ---------------------------------------------------------------------------
# Install path
# ---------------------------------------------------------------------------

log "==> meta-data-mcp systemd install"
log "    service:  $SERVICE_NAME"
log "    user:     $SERVICE_USER"
log "    bind:     $HOST:$PORT"
if [ -n "$SOURCE_DIR" ]; then
  log "    mode:     source checkout at $SOURCE_DIR"
else
  log "    mode:     uv tool install meta-data-mcp (from PyPI)"
fi
log ""

# 1. Service user
if id "$SERVICE_USER" >/dev/null 2>&1; then
  log "==> [1/6] user '$SERVICE_USER' already exists"
else
  log "==> [1/6] creating service user '$SERVICE_USER'"
  run useradd --system --create-home --shell /usr/sbin/nologin "$SERVICE_USER"
fi

USER_HOME=$(getent passwd "$SERVICE_USER" | cut -d: -f6)
[ -n "$USER_HOME" ] || die "could not resolve home dir for user '$SERVICE_USER'"

# Ensure ReadWritePaths in the unit actually exist before systemd tries to
# mount them, otherwise the service fails with status=226/NAMESPACE.
run sudo -u "$SERVICE_USER" mkdir -p "$USER_HOME/.cache" "$USER_HOME/.local/share"

# PLUGIN_WRITE_PATHS is populated below in the --source branch (and stays
# empty in the PyPI-install branch). Default to empty so the unit template
# works either way.
PLUGIN_WRITE_PATHS=""

# 2. uv (for the service user)
log "==> [2/6] ensuring uv is available for '$SERVICE_USER'"
if [ "$DRY_RUN" -eq 0 ] && ! sudo -u "$SERVICE_USER" bash -lc 'command -v uv >/dev/null'; then
  run sudo -u "$SERVICE_USER" bash -lc 'curl -LsSf https://astral.sh/uv/install.sh | sh'
fi

# 3. Install meta-data-mcp for the service user (skipped if --source given)
if [ -z "$SOURCE_DIR" ]; then
  log "==> [3/6] installing meta-data-mcp for '$SERVICE_USER' via uv tool install"
  run sudo -u "$SERVICE_USER" bash -lc 'uv tool install --force meta-data-mcp'
  EXEC_START="$USER_HOME/.local/bin/meta-data-mcp run --transport sse --host $HOST --port $PORT"
else
  [ -d "$SOURCE_DIR" ] || die "--source dir does not exist: $SOURCE_DIR"
  log "==> [3/6] using source checkout at $SOURCE_DIR (no PyPI install)"
  if [ "$DRY_RUN" -eq 0 ]; then
    # The service user needs read+write on the source dir (uv builds .venv
    # there). chown if it isn't already owned; harmless when it already is.
    chown -R "$SERVICE_USER:$SERVICE_USER" "$SOURCE_DIR"
    log "    pre-building venv (uv sync --frozen --no-dev) as $SERVICE_USER"
    sudo -u "$SERVICE_USER" bash -lc "cd '$SOURCE_DIR' && uv sync --frozen --no-dev" >/dev/null
  fi
  # --no-sync at runtime: the venv is built; ProtectSystem=strict makes /opt
  # read-only at run-time, so we must not let `uv run` try to re-sync.
  EXEC_START="$USER_HOME/.local/bin/uv --directory $SOURCE_DIR run --no-sync meta-data-mcp run --transport sse --host $HOST --port $PORT"
  # When running from a source checkout, opendata-create-plugin needs to
  # write new plugin specs and provider modules back into the source tree.
  # ProtectSystem=strict would block that, so expose the two specific
  # directories as ReadWritePaths.
  PLUGIN_WRITE_PATHS="$SOURCE_DIR/tools/specs $SOURCE_DIR/meta_data_mcp/providers"
fi

# 4. Bearer token + env file
log "==> [4/6] writing env file at $ENV_FILE"
run mkdir -p "$ENV_DIR"
EXISTING_TOKEN=""
if [ -f "$ENV_FILE" ] && [ "$DRY_RUN" -eq 0 ]; then
  EXISTING_TOKEN=$(grep -E '^META_DATA_MCP_AUTH_TOKEN=' "$ENV_FILE" | cut -d= -f2- || true)
fi

if [ -n "$TOKEN" ]; then
  FINAL_TOKEN="$TOKEN"
  TOKEN_SOURCE="provided via --token"
elif [ "$ROTATE_TOKEN" -eq 1 ] || [ -z "$EXISTING_TOKEN" ]; then
  FINAL_TOKEN=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p -c 64)
  [ -n "$FINAL_TOKEN" ] || die "could not generate a random token (need openssl or xxd)"
  TOKEN_SOURCE="newly generated"
else
  FINAL_TOKEN="$EXISTING_TOKEN"
  TOKEN_SOURCE="preserved from existing env file"
fi
log "    token: $TOKEN_SOURCE"

if [ "$DRY_RUN" -eq 1 ]; then
  log "    [dry-run] would write env file with META_DATA_MCP_AUTH_TOKEN=<redacted>"
else
  [ -f "$ENV_FILE" ] && cp -p "$ENV_FILE" "$ENV_FILE.bak"
  {
    echo "META_DATA_MCP_AUTH_TOKEN=$FINAL_TOKEN"
    if [ -n "$CONTACT_EMAIL" ]; then
      echo "OPENDATA_MCP_CONTACT=$CONTACT_EMAIL"
    fi
  } > "$ENV_FILE"
  chown "$SERVICE_USER:$SERVICE_USER" "$ENV_FILE"
  chmod 0600 "$ENV_FILE"
fi

# 5. systemd unit
log "==> [5/6] writing systemd unit at $UNIT_FILE"
UNIT_CONTENT=$(cat <<EOF
[Unit]
Description=meta-data-mcp SSE server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$SERVICE_USER
EnvironmentFile=$ENV_FILE
ExecStart=$EXEC_START
Restart=on-failure
RestartSec=5
# Hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=$USER_HOME/.cache $USER_HOME/.local/share $PLUGIN_WRITE_PATHS
PrivateTmp=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictSUIDSGID=true
LockPersonality=true

[Install]
WantedBy=multi-user.target
EOF
)

if [ "$DRY_RUN" -eq 1 ]; then
  log "    [dry-run] would write unit:"
  printf '%s\n' "$UNIT_CONTENT" | sed 's/^/        /'
else
  [ -f "$UNIT_FILE" ] && cp -p "$UNIT_FILE" "$UNIT_FILE.bak"
  printf '%s\n' "$UNIT_CONTENT" > "$UNIT_FILE"
  chmod 0644 "$UNIT_FILE"
fi

# 6. Reload + (optionally) start
log "==> [6/6] reloading systemd"
run systemctl daemon-reload

if [ "$START" -eq 1 ]; then
  log "    enabling + starting $SERVICE_NAME"
  run systemctl enable --now "$SERVICE_NAME"
  if [ "$DRY_RUN" -eq 0 ]; then
    sleep 1
    systemctl --no-pager status "$SERVICE_NAME" | head -20 || true
  fi
else
  log "    not starting (pass --start to enable + start now)"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

log ""
log "==> Done."
log ""
log "Service user:    $SERVICE_USER ($USER_HOME)"
log "Env file:        $ENV_FILE"
log "Unit:            $UNIT_FILE"
log "Listen address:  $HOST:$PORT (loopback — put TLS in front, see docs/hosting.md)"
log ""
if [ "$DRY_RUN" -eq 0 ]; then
  log "Bearer token (paste into your MCP client's Authorization header):"
  log ""
  log "    $FINAL_TOKEN"
  log ""
  log "Test:"
  log "    curl -i http://$HOST:$PORT/                              # 200 (health, no auth)"
  log "    curl -i http://$HOST:$PORT/sse                           # 401 (no token)"
  log "    curl -i -H 'Authorization: Bearer $FINAL_TOKEN' \\"
  log "         http://$HOST:$PORT/sse                              # 200 (SSE stream)"
fi
