import csv
from django.contrib import admin
from django.http import HttpResponse
from .forms import ModerationForm
from .models import Receipt


@admin.register(Receipt)
class ReceiptAdmin(admin.ModelAdmin):
    form = ModerationForm
    list_display = ["id", "user", "amount", "status", "purchased_at", "created_at", "is_demo"]
    list_filter = ["status", "is_demo", "purchased_at"]
    search_fields = ["fn", "fd", "fp", "user__username"]
    readonly_fields = ["user", "fn", "fd", "fp", "purchased_at", "amount", "created_at", "is_demo"]
    list_select_related = ["user"]
    actions = ["export_accepted"]

    def has_add_permission(self, request):
        return False

    @admin.action(description="Выгрузить принятые чеки в CSV", permissions=["view"])
    def export_accepted(self, request, queryset):
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="accepted-receipts.csv"'
        response.write("\ufeff")
        writer = csv.writer(response)
        writer.writerow(["ID", "ФН", "ФД", "ФП", "Дата покупки", "Сумма", "Дата регистрации"])
        for receipt in queryset.filter(status=Receipt.Status.ACCEPTED):
            writer.writerow([receipt.pk, receipt.fn, receipt.fd, receipt.fp, receipt.purchased_at.isoformat(), str(receipt.amount), receipt.created_at.isoformat()])
        return response
