from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth.models import User, Permission
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import ModerationForm, ReceiptForm
from .models import Receipt


@override_settings(PROMO_START="2026-10-01", PROMO_END="2026-10-31", TIME_ZONE="Europe/Moscow")
class ReceiptTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("owner", password="TestsOnly2026!")
        self.other = User.objects.create_user("other", password="TestsOnly2026!")
        self.client.force_login(self.owner)
        self.data = {"fn": "1234567890123456", "fd": "10", "fp": "1000", "purchased": "2026-10-07T12:30", "amount": "1000.00"}

    def create_receipt(self, user=None, **changes):
        values = {"user": user or self.owner, "fn": self.data["fn"], "fd": self.data["fd"], "fp": self.data["fp"], "purchased_at": datetime(2026, 10, 7, 12, 30, tzinfo=ZoneInfo("Europe/Moscow")), "amount": "1000.00"}
        values.update(changes)
        return Receipt.objects.create(**values)

    def post(self, **changes):
        return self.client.post(reverse("receipt-new"), self.data | changes, HTTP_ACCEPT="application/json")

    def test_valid_receipt_and_untrusted_fields(self):
        response = self.post(user=self.other.pk, status="accepted", rejection_reason="hack")
        self.assertEqual(response.status_code, 201)
        receipt = Receipt.objects.get(pk=response.json()["id"])
        self.assertEqual(receipt.user_id, self.owner.pk)
        self.assertEqual(receipt.status, "pending")
        self.assertEqual(receipt.rejection_reason, "")

    def test_minimum_amount_and_comma(self):
        self.assertEqual(self.post(amount="999.99").status_code, 400)
        self.assertEqual(self.post(amount="1000,00").status_code, 201)

    def test_decimal_precision(self):
        self.assertEqual(self.post(amount="1000.001").status_code, 400)

    def test_required_fields(self):
        response = self.client.post(reverse("receipt-new"), {}, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()["errors"]), {"fn", "fd", "fp", "amount", "purchased"})

    def test_numeric_fields(self):
        for field, value in [("fn", "123"), ("fd", "abc"), ("fp", "12x")]:
            with self.subTest(field=field):
                self.assertIn(field, self.post(**{field:value}).json()["errors"])

    def test_period_boundaries_and_timezone(self):
        for value in ["2026-10-01T00:00", "2026-10-31T23:59"]:
            form = ReceiptForm(self.data | {"purchased": value})
            self.assertTrue(form.is_valid(), form.errors)
            self.assertEqual(str(form.cleaned_data["purchased"].tzinfo), "Europe/Moscow")
        for value in ["2026-09-30T23:59", "2026-11-01T00:00", "invalid"]:
            self.assertFalse(ReceiptForm(self.data | {"purchased":value}).is_valid())

    def test_duplicate_including_rejected_other_owner(self):
        self.create_receipt(self.other, status="rejected", rejection_reason="Магазин не участвует")
        response = self.post()
        self.assertEqual(response.status_code, 400)
        self.assertIn("уже зарегистрирован", response.json()["errors"]["__all__"][0])

    def test_database_duplicate_race_is_readable(self):
        self.create_receipt(self.other)
        with patch("django.db.models.query.QuerySet.exists", return_value=False):
            response = self.post()
        self.assertEqual(response.status_code, 400)
        self.assertIn("уже зарегистрирован", response.json()["errors"]["__all__"][0])

    def test_database_constraints(self):
        self.create_receipt()
        for changes in [{}, {"fd":"11", "amount":"1.00"}, {"fd":"12", "status":"rejected"}, {"fd":"13", "status":"won"}]:
            with self.subTest(changes=changes), self.assertRaises(IntegrityError), transaction.atomic():
                self.create_receipt(**changes)

    def test_owner_isolation_and_ignored_parameters(self):
        mine = self.create_receipt()
        theirs = self.create_receipt(self.other, fd="22")
        response = self.client.get(reverse("receipts-api"), {"user_id":self.other.pk,"user":self.other.pk,"demo":"filled"})
        self.assertEqual([row["id"] for row in response.json()["results"]], [mine.pk])
        page = self.client.get(reverse("receipt-list"), {"user_id":self.other.pk, "demo":"filled"})
        self.assertEqual([receipt.pk for receipt in page.context["page_obj"]], [mine.pk])
        self.assertNotIn(theirs.pk, [row["id"] for row in response.json()["results"]])

    def test_pagination_and_order(self):
        for index in range(12):
            self.create_receipt(fd=str(100+index))
        first = self.client.get(reverse("receipts-api")).json()
        second = self.client.get(reverse("receipts-api"), {"page":2}).json()
        self.assertEqual(first["count"],12)
        self.assertEqual(len(first["results"]),10)
        self.assertEqual(len(second["results"]),2)
        self.assertGreater(first["results"][0]["id"],first["results"][-1]["id"])
        self.assertEqual(self.client.get(reverse("receipts-api"), {"page":"bad"}).status_code,200)

    def test_anonymous_access(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("receipts-api")).status_code,401)
        self.assertEqual(self.client.get(reverse("receipt-list")).status_code,302)
        self.assertEqual(self.post().status_code,401)

    def test_moderation_reason_and_cleanup(self):
        receipt = self.create_receipt()
        rejected = ModerationForm({"status":"rejected","rejection_reason":"  "},instance=receipt)
        # Use the same editable fields as ReceiptAdmin.
        rejected.fields = {key:field for key,field in rejected.fields.items() if key in {"status","rejection_reason"}}
        self.assertFalse(rejected.is_valid())
        self.assertIn("rejection_reason", rejected.errors)
        accepted = ModerationForm({"status":"accepted","rejection_reason":"old reason"},instance=receipt)
        accepted.fields = {key:field for key,field in accepted.fields.items() if key in {"status","rejection_reason"}}
        self.assertTrue(accepted.is_valid(),accepted.errors)
        self.assertEqual(accepted.cleaned_data["rejection_reason"],"")

    def test_staff_moderation(self):
        receipt = self.create_receipt()
        moderator = User.objects.create_user("moderator",password="TestsOnly2026!",is_staff=True)
        moderator.user_permissions.set(Permission.objects.filter(content_type__app_label="receipts",codename__in=["view_receipt","change_receipt"]))
        self.client.force_login(moderator)
        url = reverse("admin:receipts_receipt_change",args=[receipt.pk])
        bad = self.client.post(url,{"status":"rejected","rejection_reason":"","_save":"Save"})
        self.assertEqual(bad.status_code,200)
        receipt.refresh_from_db()
        self.assertEqual(receipt.status,"pending")
        good = self.client.post(url,{"status":"rejected","rejection_reason":"Магазин не участвует","_save":"Save"})
        self.assertEqual(good.status_code,302)
        receipt.refresh_from_db()
        self.assertEqual(receipt.rejection_reason,"Магазин не участвует")
        self.assertEqual(self.client.post(url,{"status":"accepted","rejection_reason":"stale","_save":"Save"}).status_code,302)
        receipt.refresh_from_db()
        self.assertEqual(receipt.rejection_reason,"")

    def test_csrf(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        self.assertEqual(client.post(reverse("receipt-new"),self.data,HTTP_ACCEPT="application/json").status_code,403)

    def test_registration_login_logout(self):
        self.client.logout()
        response = self.client.post(reverse("register"), {"username":"newuser","first_name":"Иван","email":"test@example.invalid","password1":"BlueRiver9!2026","password2":"BlueRiver9!2026"})
        self.assertEqual(response.status_code,302)
        self.assertTrue(User.objects.filter(username="newuser").exists())
        self.assertEqual(self.client.get(reverse("receipt-list")).status_code,200)
        self.assertEqual(self.client.post(reverse("logout")).status_code,302)
        self.assertEqual(self.client.post(reverse("login"),{"username":"newuser","password":"BlueRiver9!2026"}).status_code,302)

    def test_csv_exports_only_accepted(self):
        from django.contrib.admin.sites import AdminSite
        from django.test import RequestFactory
        from .admin import ReceiptAdmin
        accepted = self.create_receipt(status="accepted")
        pending = self.create_receipt(fd="200")
        response = ReceiptAdmin(Receipt, AdminSite()).export_accepted(RequestFactory().get("/admin/"), Receipt.objects.filter(pk__in=[accepted.pk, pending.pk]))
        content = response.content.decode("utf-8-sig")
        self.assertIn(f"{accepted.pk},", content)
        self.assertNotIn(f"{pending.pk},", content)
