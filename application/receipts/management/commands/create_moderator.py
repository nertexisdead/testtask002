from getpass import getpass
from django.contrib.auth.models import User, Permission
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


class Command(BaseCommand):
    help = "Create a staff moderator with receipt view/change permissions."

    def add_arguments(self, parser):
        parser.add_argument("username")

    def handle(self, *args, **options):
        username = options["username"]
        if User.objects.filter(username=username).exists():
            raise CommandError("Пользователь уже существует.")
        password = getpass("Пароль: ")
        if password != getpass("Повторите пароль: "):
            raise CommandError("Пароли не совпадают.")
        user = User(username=username, is_staff=True)
        try:
            validate_password(password, user)
        except ValidationError as error:
            raise CommandError("; ".join(error.messages))
        with transaction.atomic():
            user.set_password(password)
            user.save()
            user.user_permissions.set(Permission.objects.filter(content_type__app_label="receipts", codename__in=["view_receipt", "change_receipt"]))
        self.stdout.write(self.style.SUCCESS(f"Модератор {username} создан."))
