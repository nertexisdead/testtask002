"""Reversible demo data. Demo accounts cannot log in until a password is set."""
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import migrations


DEMO_USERS = ["demo_elena", "demo_alexey"]


def seed(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    Receipt = apps.get_model("receipts", "Receipt")
    alias = schema_editor.connection.alias
    start = date.fromisoformat(settings.PROMO_START)
    end = date.fromisoformat(settings.PROMO_END)
    if end < start:
        raise ValueError("PROMO_END must not precede PROMO_START")
    span = (end - start).days + 1
    zone = ZoneInfo(settings.TIME_ZONE)
    statuses = ["pending", "accepted", "accepted", "rejected"]
    amounts = ["1000.00", "1249.90", "3500.00", "12000.00", "2199.50", "5670.25"]
    for user_index, username in enumerate(DEMO_USERS):
        user, created = User.objects.using(alias).get_or_create(username=username, defaults={
            "first_name": "Елена" if user_index == 0 else "Алексей",
            "last_name": "Демо", "email": f"{username}@example.invalid",
            "password": "!demo-account", "is_staff": False, "is_superuser": False,
        })
        if not created:
            raise ValueError(f"Demo username already exists: {username}")
        count = 24 if user_index == 0 else 6
        for index in range(count):
            purchased = datetime.combine(start + timedelta(days=index % span), time(10 + index % 8, index % 60), tzinfo=zone)
            status = statuses[index % len(statuses)]
            Receipt.objects.using(alias).create(
                user_id=user.pk, fn=f"99990000{user_index:02d}{index:06d}",
                fd=str(100000 + user_index * 1000 + index), fp=str(900000000 + user_index * 1000 + index),
                purchased_at=purchased, created_at=purchased + timedelta(hours=1),
                amount=Decimal(amounts[index % len(amounts)]), status=status,
                rejection_reason=("Магазин не участвует в акции." if index % 8 == 3 else "Реквизиты чека не прошли проверку.") if status == "rejected" else "",
                is_demo=True,
            )


def unseed(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    Receipt = apps.get_model("receipts", "Receipt")
    alias = schema_editor.connection.alias
    Receipt.objects.using(alias).filter(is_demo=True, user__username__in=DEMO_USERS).delete()
    for user in User.objects.using(alias).filter(username__in=DEMO_USERS, password="!demo-account", is_staff=False, is_superuser=False):
        if not Receipt.objects.using(alias).filter(user_id=user.pk).exists():
            user.delete(using=alias)


class Migration(migrations.Migration):
    dependencies = [("receipts", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]
