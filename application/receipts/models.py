from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.utils import timezone


class Receipt(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "На проверке"
        ACCEPTED = "accepted", "Принят"
        REJECTED = "rejected", "Отклонён"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="receipts", verbose_name="Пользователь")
    fn = models.CharField("ФН", max_length=16, validators=[RegexValidator(r"^\d{16}$", "ФН должен содержать 16 цифр")])
    fd = models.CharField("ФД", max_length=10, validators=[RegexValidator(r"^\d{1,10}$", "ФД должен содержать от 1 до 10 цифр")])
    fp = models.CharField("ФП", max_length=10, validators=[RegexValidator(r"^\d{1,10}$", "ФП должен содержать от 1 до 10 цифр")])
    purchased_at = models.DateTimeField("Дата покупки")
    amount = models.DecimalField("Сумма", max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("1000.00"))])
    status = models.CharField("Статус", max_length=10, choices=Status.choices, default=Status.PENDING)
    rejection_reason = models.TextField("Причина отказа", blank=True)
    created_at = models.DateTimeField("Дата регистрации", default=timezone.now, editable=False)
    is_demo = models.BooleanField("Тестовый чек", default=False, editable=False)

    class Meta:
        verbose_name = "Чек"
        verbose_name_plural = "Чеки"
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.UniqueConstraint(fields=["fn", "fd", "fp"], name="receipt_unique_fiscal_details"),
            models.CheckConstraint(condition=models.Q(amount__gte=1000), name="receipt_minimum_amount"),
            models.CheckConstraint(condition=~models.Q(status="rejected") | ~models.Q(rejection_reason=""), name="receipt_rejected_requires_reason"),
            models.CheckConstraint(condition=models.Q(status__in=["pending", "accepted", "rejected"]), name="receipt_valid_status"),
        ]

    @property
    def status_icon(self):
        return {"pending": "◷", "accepted": "✓", "rejected": "×"}[self.status]

    @property
    def info(self):
        return self.rejection_reason or ("Чек принят" if self.status == self.Status.ACCEPTED else "Чек на проверке")

    def __str__(self):
        return f"Чек {self.fd} — {self.amount} ₽"
