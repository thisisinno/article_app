# Jesca Social Work

Jesca Social Work is a Django and Next.js editorial social application. Django owns authentication, data, media, permissions, engagement, notifications, and administration; the Next.js App Router provides the web UI and production PWA.

## Codespaces frontend

The frontend always connects to the deployed Django application through its same-origin Next.js API and media proxy. No frontend environment file or local Django process is required.

```bash
cd frontend
npm ci
npm run check-port
npm run dev
```

Open the forwarded Codespaces port 3000. The development command is fixed to that port and will fail clearly if another process owns it. During development, Insight unregisters its service worker and removes only `insight-` caches so stale chunks cannot break CSS or JavaScript.

## Verification

```bash
cd frontend
npm run typecheck
npm test
npm run build

cd ../backend
python manage.py check
python manage.py makemigrations --check --dry-run
```

## Backend deployment

Configure `SECRET_KEY`, `DATABASE_URL`, and `DEBUG=0` securely on the server. Before the first deployment containing the committed migrations:

1. Back up PostgreSQL.
2. Inspect `django_migrations` and compare every existing application table, column, index, and constraint with the migrations.
3. If tables already exist and match exactly, run `python manage.py migrate --fake-initial`; otherwise resolve schema differences first.
4. For a normal migration state, run `python manage.py migrate`.
5. Run `python manage.py collectstatic --noinput` and restart the Django application service.

Do not use `--fake-initial` without the schema comparison. It does not verify that an existing table matches the migration.

## Deprecated data

The legacy `messaging` and follow models remain installed only to preserve production tables. Their HTTP and WebSocket routes are no longer exposed, and the current product does not read or write those tables. Do not drop them without a separately reviewed data-retention migration.
