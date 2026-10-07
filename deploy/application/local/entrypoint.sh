#!/bin/sh
set -euo pipefail

get_db_setting() {
  python3 - "$DB_CONFIG_PATH" "$1" <<'PY'
import runpy
import sys
value = runpy.run_path(sys.argv[1])["DATABASES"]["default"][sys.argv[2]]
print(value)
PY
}

run_as_application() {
  su-exec "$APPLICATION_USER:$APPLICATION_GROUP" "$@"
}

VENV_PATH="${VENV_PATH-}"
DB_CONFIG_PATH="${DB_CONFIG_PATH-}"
LOGROTATE_CONFIG_PATH="${LOGROTATE_CONFIG_PATH-}"
DB_WAIT_TIMEOUT="${DB_WAIT_TIMEOUT-}"
SUPERVISOR_CONF="${SUPERVISOR_CONF-}"
SUPERVISORD_BIN="${SUPERVISORD_BIN-}"
APPLICATION_USER="${APPLICATION_USER-}"
APPLICATION_GROUP="${APPLICATION_GROUP-}"
APPLICATION_HOME="${APPLICATION_HOME-}"
DB_HOST=$(get_db_setting HOST)
DB_PORT=$(get_db_setting PORT)
DB_USER=$(get_db_setting USER)
DB_NAME=$(get_db_setting NAME)
DB_PASSWORD=$(get_db_setting PASSWORD)

REQUIRED_VARIABLE_NAMES="
APPLICATION_PATH
VENV_PATH
DB_CONFIG_PATH
LOGROTATE_CONFIG_PATH
DB_WAIT_TIMEOUT
SUPERVISOR_CONF
APPLICATION_USER
APPLICATION_GROUP
APPLICATION_HOME
ENTRYPOINT_PATH
DB_HOST
DB_PORT
DB_USER
DB_NAME
DB_PASSWORD
"

for var in $REQUIRED_VARIABLE_NAMES; do
  eval "value=\${$var}"
  if [ -z "$value" ]; then
    echo "[entrypoint] Missing required environment variable: $var" >&2
    exit 1
  fi
done

echo "[entrypoint] Preparing application directories"
install -d -o "$APPLICATION_USER" -g "$APPLICATION_GROUP" "$VENV_PATH"
install -d -o "$APPLICATION_USER" -g "$APPLICATION_GROUP" /runtime/static_collected
install -d -o "$APPLICATION_USER" -g "$APPLICATION_GROUP" "$APPLICATION_PATH/media"
chown -R "$APPLICATION_USER:$APPLICATION_GROUP" "$VENV_PATH" /runtime/static_collected

if [ ! -f "$VENV_PATH/.docker-managed" ]; then
  echo "[entrypoint] Virtualenv $VENV_PATH is not managed by docker. Clearing its contents"
  find "$VENV_PATH" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
fi

if [ ! -x "$VENV_PATH/bin/python3" ]; then
  echo "[entrypoint] Creating virtualenv at $VENV_PATH"
  run_as_application python3 -m venv "$VENV_PATH"
  run_as_application touch "$VENV_PATH/.docker-managed"
fi

echo "[entrypoint] Installing logrotate.d files"
find "$LOGROTATE_CONFIG_PATH" -maxdepth 1 -type f -exec cp -f {} /etc/logrotate.d/ \;
find /etc/logrotate.d -type f -exec chown root:root {} \;
find /etc/logrotate.d -type f -exec chmod 644 {} \;

echo "[entrypoint] Ensuring pip installation"
run_as_application "$VENV_PATH/bin/python" -m ensurepip --upgrade

echo "[entrypoint] Upgrading pip"
run_as_application "$VENV_PATH/bin/python" -m pip install --upgrade pip

echo "[entrypoint] Installing dependencies"
run_as_application "$VENV_PATH/bin/python" -m pip install --no-cache-dir -r requirements.txt

if ! command -v pg_isready >/dev/null 2>&1; then
  echo "pg_isready not found" >&2
fi

echo "[entrypoint] Checking Python dependencies"
run_as_application "$VENV_PATH/bin/python" -m pip check

if [ -n "$DB_HOST" ]; then
  echo "[entrypoint] Waiting for PostgreSQL at $DB_HOST:$DB_PORT"
  WAITED=0
  export PGPASSWORD="$DB_PASSWORD"
  until pg_isready -h "$DB_HOST" -p "$DB_PORT" -d "$DB_NAME" -U "$DB_USER" >/dev/null 2>&1; do
    if [ "$WAITED" -ge "$DB_WAIT_TIMEOUT" ]; then
      echo "[entrypoint] PostgreSQL is not ready after ${DB_WAIT_TIMEOUT}s" >&2
      exit 1
    fi
    sleep 2
    WAITED=$((WAITED + 2))
  done
fi

echo "[entrypoint] Running Django startup import test"
run_as_application "$VENV_PATH/bin/python" manage.py shell -c "import django; django.setup()" || {
  echo '[entrypoint] Django import test failed'
  exit 1
}

# echo "[entrypoint] Validating templates"
# run_as_application "$VENV_PATH/bin/python" manage.py validate_templates

echo "[entrypoint] Running collect static"
run_as_application "$VENV_PATH/bin/python" manage.py collectstatic --noinput

echo "[entrypoint] Running compile all checks"
run_as_application "$VENV_PATH/bin/python" -m compileall -f -q \
  -x "^${APPLICATION_PATH}/(static|static_collected|files|venv)/" "$APPLICATION_PATH"

echo "[entrypoint] Running internal django checks"
run_as_application "$VENV_PATH/bin/python" manage.py check --deploy

echo "[entrypoint] Checking migration plan"
run_as_application "$VENV_PATH/bin/python" manage.py migrate --plan

echo "[entrypoint] Running makemigrations checks"
run_as_application "$VENV_PATH/bin/python" manage.py makemigrations --check --dry-run

echo "[entrypoint] Running migrations"
run_as_application "$VENV_PATH/bin/python" manage.py migrate --noinput

echo "[entrypoint] Checking supervisord existence in $SUPERVISORD_BIN"
if [ ! -x "$SUPERVISORD_BIN" ]; then
  echo "[entrypoint] Supervisord not found at $SUPERVISORD_BIN" >&2
  exit 1
else
  echo "[entrypoint] Supervisord found at $SUPERVISORD_BIN"
fi

echo "[entrypoint] Checking supervisor config existence"
if [ ! -f "$SUPERVISOR_CONF" ]; then
  echo "[entrypoint] Missing supervisor config at $SUPERVISOR_CONF" >&2
  exit 1
else
  echo "[entrypoint] Supervisor config found at $SUPERVISOR_CONF"
fi

echo "[entrypoint] Starting server via supervisord"
exec "$SUPERVISORD_BIN" -n -c "$SUPERVISOR_CONF"
