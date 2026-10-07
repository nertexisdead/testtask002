"""Keep preview receipts in the configured period and their registrations in the past."""
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo
from django.conf import settings
from django.db import migrations
from django.utils import timezone


def update_demo(apps, schema_editor):
    Receipt = apps.get_model("receipts", "Receipt")
    now = timezone.now()
    zone = ZoneInfo(settings.TIME_ZONE)
    start = date.fromisoformat(settings.PROMO_START)
    end = date.fromisoformat(settings.PROMO_END)
    last = max(start, min(end, now.astimezone(zone).date() - timedelta(days=1)))
    span = (last - start).days + 1
    receipts = list(Receipt.objects.using(schema_editor.connection.alias).filter(is_demo=True).order_by("pk"))
    for index, receipt in enumerate(receipts):
        receipt.purchased_at = datetime.combine(start + timedelta(days=index % span), time(12, index % 60), tzinfo=zone)
        receipt.created_at = now - timedelta(days=1, minutes=len(receipts) - index)
        receipt.save(using=schema_editor.connection.alias, update_fields=["purchased_at", "created_at"])


class Migration(migrations.Migration):
    dependencies = [("receipts", "0002_demo_receipts")]
    operations = [migrations.RunPython(update_demo, migrations.RunPython.noop)]
