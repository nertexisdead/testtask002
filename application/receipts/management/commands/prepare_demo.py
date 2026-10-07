import os
from django.contrib.auth.models import User, Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Enable local demo accounts using passwords supplied in .env."

    def handle(self, *args, **options):
        password = os.getenv("DEMO_PASSWORD")
        moderator_password = os.getenv("DEMO_MODERATOR_PASSWORD")
        if not password or not moderator_password:
            raise CommandError("Set DEMO_PASSWORD and DEMO_MODERATOR_PASSWORD in .env first.")
        with transaction.atomic():
            for username in ["demo_elena", "demo_alexey"]:
                user = User.objects.get(username=username, email=f"{username}@example.invalid")
                user.set_password(password)
                user.save(update_fields=["password"])
            moderator, created = User.objects.get_or_create(username="demo_moderator", defaults={"email":"demo_moderator@example.invalid"})
            if not created and moderator.email != "demo_moderator@example.invalid":
                raise CommandError("Moderator username is already in use.")
            moderator.is_staff = True
            moderator.set_password(moderator_password)
            moderator.save()
            moderator.user_permissions.set(Permission.objects.filter(content_type__app_label="receipts",codename__in=["view_receipt","change_receipt"]))
        self.stdout.write(self.style.SUCCESS("Local demo accounts are ready."))
