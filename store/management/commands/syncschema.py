from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = "Adds tables/columns that exist in the models but not in the database (safety net when migrations are not committed to git)."
    def handle(self, *args, **options):
        tables = set(connection.introspection.table_names())
        for model in apps.get_app_config("store").get_models():
            t = model._meta.db_table
            if t not in tables:
                with connection.schema_editor() as se: se.create_model(model)
                self.stdout.write(f"created table {t}"); continue
            with connection.cursor() as cur: have = {c.name for c in connection.introspection.get_table_description(cur, t)}
            for f in model._meta.local_fields:
                if f.column not in have:
                    with connection.schema_editor() as se: se.add_field(model, f)
                    self.stdout.write(f"added column {t}.{f.column}")
        self.stdout.write("Database schema is in sync.")
