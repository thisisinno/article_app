from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


REQUIRED = {
    "accounts.User": {"public_id", "display_name", "is_staff", "is_superuser"},
    "accounts.Profile": {"avatar", "cover_image", "bio", "verified"},
    "accounts.AnonymousVisitor": set(),
    "publishing.Category": set(),
    "publishing.Post": {
        "category_id", "post_type", "status", "published_at",
        "published_notification_sent_at", "view_count", "like_count",
        "comment_count", "repost_count", "bookmark_count", "share_count",
    },
    "publishing.Comment": set(),
    "interactions.PostLike": set(),
    "interactions.PostBookmark": set(),
    "interactions.PostView": set(),
    "interactions.PostShare": set(),
    "interactions.CommentLike": set(),
    "interactions.Notification": set(),
}


class Command(BaseCommand):
    help = "Read-only audit of critical model tables, columns, and migration state."

    def handle(self, *args, **options):
        problems = []
        with connection.cursor() as cursor:
            tables = set(connection.introspection.table_names(cursor))
            for label, required_names in REQUIRED.items():
                model = apps.get_model(label)
                table = model._meta.db_table
                if table not in tables:
                    problems.append(f"missing table: {table}")
                    continue
                actual = {
                    col.name for col in connection.introspection.get_table_description(cursor, table)
                }
                expected = {
                    field.column for field in model._meta.local_fields
                }
                required = set()
                field_names = {field.name for field in model._meta.local_fields}
                for name in required_names:
                    if name in field_names:
                        required.add(model._meta.get_field(name).column)
                    elif name.endswith("_id") and name[:-3] in field_names:
                        required.add(model._meta.get_field(name[:-3]).column)
                    else:
                        required.add(name)
                for column in sorted((expected | required) - actual):
                    problems.append(f"missing column: {table}.{column}")

        executor = MigrationExecutor(connection)
        targets = executor.loader.graph.leaf_nodes()
        plan = executor.migration_plan(targets)
        for migration, backwards in plan:
            if not backwards:
                problems.append(f"unapplied migration: {migration.app_label}.{migration.name}")

        if problems:
            for problem in problems:
                self.stderr.write(self.style.ERROR(problem))
            raise CommandError(f"Schema audit failed with {len(problems)} problem(s). No data was changed.")
        self.stdout.write(self.style.SUCCESS("Schema audit passed. Critical tables, columns, and migrations match."))
