from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from .forms import ReceiptForm
from .models import Receipt


def json_request(request):
    return "application/json" in request.headers.get("Accept", "")


@login_required
@require_GET
def receipt_list(request):
    sort = request.GET.get("sort", "registered")
    mapping = {"registered": "created_at", "purchased": "purchased_at", "amount": "amount", "status": "status"}
    if sort not in mapping:
        sort = "registered"
    direction = "asc" if request.GET.get("direction") == "asc" else "desc"
    prefix = "" if direction == "asc" else "-"
    receipts = Receipt.objects.filter(user=request.user).order_by(prefix + mapping[sort], prefix + "pk")
    return render(request, "receipts/list.html", {
        "page_obj": Paginator(receipts, 10).get_page(request.GET.get("page")),
        "receipt_count": receipts.count(), "sort": sort, "direction": direction,
        "next_direction": "desc" if direction == "asc" else "asc",
        "columns": [{"key": key, "label": label} for key, label in [
            ("purchased", "Дата покупки"), ("status", "Статус"),
            ("amount", "Сумма чека"), ("registered", "Дата регистрации"),
        ]],
    })


@require_http_methods(["GET", "POST"])
def receipt_new(request):
    if not request.user.is_authenticated:
        if json_request(request):
            return JsonResponse({"ok": False, "message": "Войдите в аккаунт, чтобы зарегистрировать чек."}, status=401)
        return redirect("login")
    data = request.POST.copy() if request.method == "POST" else None
    if data is not None:
        data["amount"] = data.get("amount", "").replace(",", ".")
    form = ReceiptForm(data)
    if request.method == "POST" and form.is_valid():
        receipt = form.save(commit=False)
        receipt.user = request.user
        receipt.status = Receipt.Status.PENDING
        receipt.rejection_reason = ""
        try:
            with transaction.atomic():
                receipt.save()
        except IntegrityError as error:
            if getattr(getattr(error.__cause__, "diag", None), "constraint_name", None) != "receipt_unique_fiscal_details":
                raise
            form.add_error(None, "Этот чек уже зарегистрирован. Повторная отправка недоступна.")
        else:
            if json_request(request):
                return JsonResponse({"ok": True, "id": receipt.pk, "redirect": "/receipts/success/"}, status=201)
            return redirect("receipt-success")
    if request.method == "POST" and json_request(request):
        return JsonResponse({"ok": False, "errors": {field: list(errors) for field, errors in form.errors.items()}}, status=400)
    return render(request, "receipts/form.html", {"form": form}, status=400 if request.method == "POST" else 200)


@login_required
@require_GET
def receipt_success(request):
    return render(request, "receipts/success.html")


@require_GET
def receipts_api(request):
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Требуется авторизация."}, status=401)
    page = Paginator(Receipt.objects.filter(user=request.user).order_by("-created_at", "-pk"), 10).get_page(request.GET.get("page"))
    return JsonResponse({
        "count": page.paginator.count, "page": page.number, "pages": page.paginator.num_pages,
        "results": [{
            "id": receipt.pk, "fn": receipt.fn, "fd": receipt.fd, "fp": receipt.fp,
            "purchased_at": receipt.purchased_at.isoformat(), "amount": str(receipt.amount),
            "status": receipt.status, "status_label": receipt.get_status_display(),
            "rejection_reason": receipt.rejection_reason, "created_at": receipt.created_at.isoformat(),
        } for receipt in page],
    })
