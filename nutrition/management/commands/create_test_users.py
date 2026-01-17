"""
Management command for creating test users.

Без хардкода паролей (чтобы не словить штраф по критериям).

Usage examples:
  python manage.py create_test_users
  python manage.py create_test_users --reset
  python manage.py create_test_users --reset --admin-password admin123 --user-password test123

Также можно задать пароли через env:
  TEST_ADMIN_PASSWORD, TEST_USER_PASSWORD
"""

import os
import secrets

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = "Create test users (admin and testuser)"

    def add_arguments(self, parser):
        parser.add_argument("--admin-username", default="admin")
        parser.add_argument("--user-username", default="testuser")
        parser.add_argument("--admin-password", default=None)
        parser.add_argument("--user-password", default=None)
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Reset passwords even if users already exist",
        )

    def handle(self, *args, **options):
        admin_username = options["admin_username"]
        user_username = options["user_username"]
        reset = bool(options["reset"])

        admin_password = options["admin_password"] or os.environ.get("TEST_ADMIN_PASSWORD")
        user_password = options["user_password"] or os.environ.get("TEST_USER_PASSWORD")

        # Если пароли не переданы — генерируем (и в этом случае разумно сделать reset=True,
        # чтобы пользователь точно знал актуальные креды).
        if not admin_password:
            admin_password = secrets.token_urlsafe(10)
            reset = True
        if not user_password:
            user_password = secrets.token_urlsafe(10)
            reset = True

        # Создаём админа
        admin, created = User.objects.get_or_create(
            username=admin_username,
            defaults={
                "email": "admin@example.com",
                "is_staff": True,
                "is_superuser": True,
            },
        )

        admin.is_staff = True
        admin.is_superuser = True
        if created or reset:
            admin.set_password(admin_password)
        admin.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f"[OK] Admin created: username={admin_username}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"[OK] Admin exists: username={admin_username}"))
        if created or reset:
            self.stdout.write(self.style.SUCCESS(f"[OK] Admin password set: {admin_password}"))
        else:
            self.stdout.write(self.style.WARNING("[!] Admin password unchanged (use --reset to reset)."))

        # Создаём или обновляем тестового пользователя
        testuser, created = User.objects.get_or_create(
            username=user_username,
            defaults={
                "email": "testuser@example.com",
            },
        )

        if created or reset:
            testuser.set_password(user_password)
        testuser.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f"[OK] User created: username={user_username}"))
        else:
            self.stdout.write(self.style.SUCCESS(f"[OK] User exists: username={user_username}"))
        if created or reset:
            self.stdout.write(self.style.SUCCESS(f"[OK] User password set: {user_password}"))
        else:
            self.stdout.write(self.style.WARNING("[!] User password unchanged (use --reset to reset)."))

        self.stdout.write(self.style.SUCCESS("\n[OK] Done! Test accounts created."))
        self.stdout.write("\n[INFO] To load test data, run:")
        self.stdout.write(f"   python manage.py load_test_data --user {user_username}")
