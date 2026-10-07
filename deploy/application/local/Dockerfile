FROM python:3.14.3-alpine@sha256:faee120f7885a06fcc9677922331391fa690d911c020abb9e8025ff3d908e510

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPYCACHEPREFIX="/tmp/python-cache" \
    APPLICATION_PATH="/application" \
    VENV_PATH="/opt/venv" \
    DB_CONFIG_PATH="/application/config/db.py" \
    LOGROTATE_CONFIG_PATH="/local-config/logrotate.d" \
    DB_WAIT_TIMEOUT="60" \
    SUPERVISOR_CONF="/etc/supervisord.conf" \
    SUPERVISORD_BIN="/opt/venv/bin/supervisord" \
    APPLICATION_USER="django" \
    APPLICATION_GROUP="django" \
    APPLICATION_HOME="/home/django" \
    ENTRYPOINT_PATH="/entrypoint.sh"

RUN addgroup -g 1000 django \
    && adduser -D -G django -u 1000 django \
    && apk add --no-cache \
        bash \
        curl \
        cairo \
        fontconfig \
        gdk-pixbuf \
        harfbuzz \
        pango \
        ttf-dejavu \
        libxml2 \
        libxslt \
        libpq \
        postgresql-client \
        build-base \
        linux-headers \
        postgresql-dev \
        libffi-dev \
        openssl-dev \
        zlib-dev \
        jpeg-dev \
        freetype-dev \
        tiff-dev \
        dcron \
        logrotate \
        su-exec \
        htop \
        mc \
        nano \
    && install -d -o django -g django ${APPLICATION_PATH} \
    && install -d -o django -g django ${VENV_PATH} \
    && install -d -o django -g django /runtime/static_collected

WORKDIR ${APPLICATION_PATH}

COPY deploy/application/local/entrypoint.sh ${ENTRYPOINT_PATH}
RUN chmod +x ${ENTRYPOINT_PATH}

ENTRYPOINT ["/entrypoint.sh"]
