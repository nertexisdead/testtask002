from django.contrib import admin
from django.urls import path

from . import views

urlpatterns = [
    path("", views.receipt_list, name="receipt-list"),
    path("receipts/new/", views.receipt_new, name="receipt-new"),
    path("receipts/success/", views.receipt_success, name="receipt-success"),
    path("admin/", admin.site.urls),
    path("health/", views.health),
]
