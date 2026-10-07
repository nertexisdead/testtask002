# Чек на удачу

Пустой Django-проект для тестового задания. Бизнес-логика и фронтенд пока не реализованы.

## Локальный запуск

Используется исходный локальный деплой: Traefik → Caddy → Django под Supervisor,
PostgreSQL, pgAdmin, Mailpit, cron и logrotate. Dockerfile и entrypoint восстановлены
из исходного проекта. Код приложения монтируется из application/.

```sh
cp .env.example .env
# Заменить DJANGO_SECRET_KEY на случайное значение.
docker compose -f docker-compose.local.yml up --build -d
```

Локальный .env уже создан. Порт APP_PORT=80 — стандартный HTTP-порт.

- Приложение: http://testtask002.localhost/health/
- Админка Django: http://testtask002.localhost/admin/
- pgAdmin: http://pgadmin.testtask002.localhost/
- Mailpit: http://mailpit.testtask002.localhost/
- Traefik: http://traefik.testtask002.localhost/

```sh
docker compose -f docker-compose.local.yml exec testtask002_application /opt/venv/bin/python manage.py createsuperuser
docker compose -f docker-compose.local.yml down
```

Имена сервисов, сети, маршрутов, БД и volumes используют testtask002.
Volumes: testtask002_application_venv, testtask002_application_static,
testtask002_application_logs, testtask002_postgresql_data, testtask002_pgadmin_data.
Сеть: testtask002_traefik_default. Media сохраняется в application/media.
Пароли БД и pgAdmin в восстановленных конфигурациях предназначены для локальной разработки.
Даты акции задаются PROMO_START/PROMO_END в .env.
