"""Views for template previews only. Receipt persistence will be added later."""
from datetime import datetime

from django.conf import settings
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods


def context():
    return {"promo_start": settings.PROMO_START, "promo_end": settings.PROMO_END}


def demo_receipts():
    statuses = {
        "pending": ("В обработке", "◷", "Чек в обработке"),
        "accepted": ("Обработан", "✓", "Чек принят"),
        "rejected": ("Ошибка", "×", "Минимальная стоимость чека должна составлять 1 000 ₽."),
        "won": ("Вы выиграли", "✦", "Поздравляем, ваш чек выиграл!"),
    }
    sequence = ["pending", "accepted", "accepted", "rejected", "won", "rejected", "pending", "won"]
    receipts = []
    for index in range(24):
        status = sequence[index % len(sequence)]
        label, icon, info = statuses[status]
        if index % len(sequence) == 5:
            info = "Товар приобретён в магазине, который не участвует в акции."
        receipts.append({
            "purchased": datetime(2026, 10, 24 - index, 12, 30),
            "registered": datetime(2026, 10, 24 - index, 14, 5),
            "amount": 12000, "status": status, "status_label": label,
            "status_icon": icon, "info": info,
        })
    return receipts


@require_GET
def receipt_list(request):
    receipts = demo_receipts() if request.GET.get("demo") == "filled" else []
    sort = request.GET.get("sort", "registered")
    if sort not in {"purchased", "registered", "amount", "status"}:
        sort = "registered"
    direction = "asc" if request.GET.get("direction") == "asc" else "desc"
    receipts.sort(key=lambda receipt: receipt[sort], reverse=direction == "desc")
    data = context()
    data.update({
        "page_obj": Paginator(receipts, 10).get_page(request.GET.get("page")),
        "receipt_count": len(receipts), "sort": sort, "direction": direction,
        "next_direction": "desc" if direction == "asc" else "asc",
        "columns": [
            {"key": "purchased", "label": "Дата покупки"},
            {"key": "status", "label": "Статус"},
            {"key": "amount", "label": "Сумма чека"},
            {"key": "registered", "label": "Дата регистрации"},
        ],
    })
    return render(request, "receipts/list.html", data)


@require_http_methods(["GET", "POST"])
def receipt_new(request):
    if request.method == "POST":
        # Preview only: do not persist or claim server validation yet.
        return redirect("receipt-success")
    return render(request, "receipts/form.html", context())


@require_GET
def receipt_success(request):
    return render(request, "receipts/success.html", context())


def health(request):
    return JsonResponse({"status": "ok"})
