# Production schema alignment

Before changing PostgreSQL, take a verified backup and inspect both the physical schema and Django's recorded state:

```bash
python manage.py showmigrations
python manage.py migrate --plan
python manage.py audit_schema
```

Review `django_migrations`, existing table names, and critical columns. Determine whether legacy tables came from `migrate --run-syncdb`. Do not use `--fake-initial` unless every table, column, constraint, and index in the initial migration has been verified to match. If an existing production table only lacks later columns, apply reviewed staged migrations instead of faking the initial migration.

After the audit and migration plan have been reviewed and the backup confirmed, run `python manage.py migrate`, rerun `python manage.py audit_schema`, and only then restart the application service.
