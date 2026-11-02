import os
from django.apps import AppConfig
from django.db.models.signals import post_migrate

def seed_if_empty(sender, **kwargs):
    """After `migrate`: fill an empty database with the catalogue, and (if ADMIN_PASSWORD is set) create/refresh the admin user."""
    try:
        from django.core.management import call_command
        from .models import Product
        if not Product.objects.exists(): call_command("seed")
    except Exception as e:  # never block migrate
        print("Auto-seed skipped:", e)
    pwd = os.getenv("ADMIN_PASSWORD")
    if pwd:
        try:
            from django.contrib.auth.models import User
            a, _ = User.objects.get_or_create(username="admin", defaults={"email": "admin@stepup.in"})
            a.is_staff = a.is_superuser = True; a.set_password(pwd); a.save()
            print("Admin user 'admin' is ready.")
        except Exception as e:
            print("Admin setup skipped:", e)

class StoreConfig(AppConfig):
    name = "store"; default_auto_field = "django.db.models.BigAutoField"
    def ready(self): post_migrate.connect(seed_if_empty, sender=self)
