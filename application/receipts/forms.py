from datetime import date, datetime
from zoneinfo import ZoneInfo

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError

from .models import Receipt


class ReceiptForm(forms.ModelForm):
    purchased = forms.CharField(label="Дата покупки")

    class Meta:
        model = Receipt
        fields = ["fn", "fd", "fp", "amount"]

    def clean_purchased(self):
        value = self.cleaned_data["purchased"]
        try:
            parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M")
        except ValueError:
            raise ValidationError("Введите корректные дату и время покупки.")
        start = date.fromisoformat(settings.PROMO_START)
        end = date.fromisoformat(settings.PROMO_END)
        if not start <= parsed.date() <= end:
            raise ValidationError("Дата покупки должна входить в период акции.")
        return parsed.replace(tzinfo=ZoneInfo(settings.TIME_ZONE))

    def clean(self):
        data = super().clean()
        if all(data.get(key) for key in ("fn", "fd", "fp")):
            if Receipt.objects.filter(fn=data["fn"], fd=data["fd"], fp=data["fp"]).exists():
                raise ValidationError("Этот чек уже зарегистрирован. Повторная отправка недоступна.")
        return data

    def save(self, commit=True):
        receipt = super().save(commit=False)
        receipt.purchased_at = self.cleaned_data["purchased"]
        if commit:
            receipt.save()
        return receipt


class ModerationForm(forms.ModelForm):
    class Meta:
        model = Receipt
        fields = "__all__"

    def clean(self):
        data = super().clean()
        reason = data.get("rejection_reason", "").strip()
        if data.get("status") == Receipt.Status.REJECTED:
            if not reason:
                self.add_error("rejection_reason", "При отклонении укажите причину отказа.")
            data["rejection_reason"] = reason
        else:
            data["rejection_reason"] = ""
        return data
