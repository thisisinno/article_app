# Insight

Insight is an editorial social publishing application built exclusively with Django 5 and the Next.js App Router. It combines public reading and anonymous participation with articles, short posts, author threads, profiles, search, session authentication, moderation, and realtime one-to-one chat. The responsive Next.js site is also an installable PWA.

## Architecture

- `backend/`: Django JSON API, session/CSRF auth, custom user model, admin, ORM models, media, anonymous visitor identity, engagement services, and Channels ASGI chat.
- `frontend/`: strict TypeScript Next.js App Router UI, CSS Modules, native fetch, service worker, manifest, offline fallback, and durable browser drafts.
- PostgreSQL is the production database. SQLite is the zero-configuration local fallback. Redis backs Channels in production (`USE_REDIS=1`).
- Public APIs live at `/api/v1/`; WebSockets use `/ws/chat/<conversation-id>/`.

The five primary routes are `/`, `/search`, `/post/[postId]`, `/chat` (with conversation state), and `/profile/[username]`. Auth, creation, settings, help, notifications, and profile editing remain dialogs or nested states.

## Local setup

Prerequisites: Python 3.12, Node 20+, npm, and optionally Docker.

```bash
docker compose up -d
python3.12 -m venv backend/env
backend/env/bin/pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
backend/env/bin/python backend/manage.py migrate
backend/env/bin/python backend/manage.py seed_demo
cp frontend/.env.local.example frontend/.env.local
cd frontend && npm install
```

For the quickest SQLite/InMemory-Channels development run, do not export `DATABASE_URL` or `USE_REDIS`:

```bash
backend/env/bin/python backend/manage.py runserver 0.0.0.0:8000
cd frontend && npm run dev
```

For PostgreSQL/Redis, export the values from `backend/.env.example` before running Django. Environment files are examples; Django does not silently parse them.

Open `http://localhost:3000`. Django admin is `http://localhost:8000/admin/`.

## Demo credentials

After `seed_demo`, use `admin` / `InsightDemo123!`. The demo accounts `eleanor`, `marcus`, and `sarah` use the same development-only password.

## Verification

```bash
backend/env/bin/python backend/manage.py check
backend/env/bin/python backend/manage.py test
backend/env/bin/python backend/manage.py reconcile_counters
cd frontend && npm run typecheck && npm run build
```

The service worker only handles public GET data and explicitly excludes auth, notifications, and conversations. Chat uses session cookies through Channels `AuthMiddlewareStack`; deploy frontend/backend under a same-site origin or configure CSRF and cookie policy carefully. Uploaded media defaults to `backend/media`; production deployments should place that behind durable object storage and a trusted image delivery origin.

## Production checklist

- Set a long random `SECRET_KEY`, `DEBUG=0`, explicit `ALLOWED_HOSTS`, HTTPS, secure cookies, and `CSRF_TRUSTED_ORIGINS`.
- Use PostgreSQL and Redis, run migrations, collect static files, and serve ASGI with Daphne.
- Put media behind private, validated S3-compatible storage and configure retention/backups.
- Add edge rate limiting and a CAPTCHA provider for sustained hostile traffic.
- Run dependency, accessibility, Lighthouse, and Playwright checks against the deployed origins.
