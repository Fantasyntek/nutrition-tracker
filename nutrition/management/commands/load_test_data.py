"""
Management command for loading test data.
Usage: python manage.py load_test_data [--user USERNAME]
"""

import datetime as dt
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from nutrition.models import FoodItem, Goal, Meal, MealItem, WeightLog

User = get_user_model()


class Command(BaseCommand):
    help = "Load test data (foods, meals, weight logs, goals)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            type=str,
            default="admin",
            help="Имя пользователя для создания данных (по умолчанию: admin)",
        )

    def handle(self, *args, **options):
        username = options["user"]
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Пользователь '{username}' не найден. Создайте его сначала."))
            return

        self.stdout.write(f"Заполнение тестовыми данными для пользователя: {user.username}")

        # 1. Создаём продукты (если их ещё нет)
        foods_data = [
            {"name": "Куриная грудка", "kcal": 165, "protein": 31, "fat": 3.6, "carb": 0},
            {"name": "Рис отварной", "kcal": 130, "protein": 2.7, "fat": 0.3, "carb": 28},
            {"name": "Брокколи", "kcal": 34, "protein": 2.8, "fat": 0.4, "carb": 7},
            {"name": "Овсянка", "kcal": 389, "protein": 16.9, "fat": 6.9, "carb": 66},
            {"name": "Банан", "kcal": 89, "protein": 1.1, "fat": 0.3, "carb": 23},
            {"name": "Яйцо куриное", "kcal": 157, "protein": 12.7, "fat": 11.5, "carb": 0.7},
            {"name": "Творог 5%", "kcal": 121, "protein": 16, "fat": 5, "carb": 3},
            {"name": "Хлеб цельнозерновой", "kcal": 247, "protein": 13, "fat": 4.2, "carb": 41},
            {"name": "Лосось", "kcal": 208, "protein": 20, "fat": 12, "carb": 0},
            {"name": "Авокадо", "kcal": 160, "protein": 2, "fat": 15, "carb": 9},
        ]

        foods = {}
        for fd in foods_data:
            obj, created = FoodItem.objects.get_or_create(
                name=fd["name"],
                defaults={
                    "kcal_per_100g": Decimal(str(fd["kcal"])),
                    "protein_per_100g": Decimal(str(fd["protein"])),
                    "fat_per_100g": Decimal(str(fd["fat"])),
                    "carb_per_100g": Decimal(str(fd["carb"])),
                    "source": FoodItem.Source.MANUAL,
                },
            )
            foods[fd["name"]] = obj
            if created:
                self.stdout.write(self.style.SUCCESS(f"  Создан продукт: {obj.name}"))

        # 2. Создаём цель (если её нет)
        today = timezone.localdate()
        goal, goal_created = Goal.objects.get_or_create(
            user=user,
            is_active=True,
            defaults={
                "start_date": today - dt.timedelta(days=14),
                "target_date": today + dt.timedelta(days=30),
                "start_weight_kg": Decimal("75.0"),
                "target_weight_kg": Decimal("70.0"),
                "daily_kcal_target": 1800,
                "daily_protein_target": 150,
                "daily_fat_target": 60,
                "daily_carb_target": 180,
            },
        )
        if goal_created:
            self.stdout.write(self.style.SUCCESS(f"  Создана цель: {goal.daily_kcal_target} ккал/день"))

        # 3. Создаём записи веса за последние 14 дней
        weight_logs_created = 0
        start_weight = float(goal.start_weight_kg)
        for i in range(14):
            date = today - dt.timedelta(days=13 - i)
            # Небольшое снижение веса (примерно 0.1 кг каждые 2 дня)
            weight = Decimal(str(start_weight - (i * 0.05)))
            _, created = WeightLog.objects.get_or_create(
                user=user,
                date=date,
                defaults={"weight_kg": weight},
            )
            if created:
                weight_logs_created += 1
        if weight_logs_created > 0:
            self.stdout.write(self.style.SUCCESS(f"  Создано записей веса: {weight_logs_created}"))

        # 4. Создаём приёмы пищи за последние 7 дней
        meals_created = 0
        meal_items_created = 0

        meal_plans = [
            # Завтрак
            [("Овсянка", 100), ("Банан", 120), ("Яйцо куриное", 100)],
            # Обед
            [("Куриная грудка", 150), ("Рис отварной", 200), ("Брокколи", 150)],
            # Ужин
            [("Лосось", 150), ("Брокколи", 100), ("Авокадо", 50)],
            # Перекус
            [("Творог 5%", 200), ("Хлеб цельнозерновой", 50)],
        ]

        for day_offset in range(7):
            date = today - dt.timedelta(days=6 - day_offset)
            meal_types = [Meal.Type.BREAKFAST, Meal.Type.LUNCH, Meal.Type.DINNER, Meal.Type.SNACK]

            for meal_type, meal_plan in zip(meal_types, meal_plans):
                meal, meal_created = Meal.objects.get_or_create(
                    user=user,
                    date=date,
                    type=meal_type,
                )
                if meal_created:
                    meals_created += 1

                # Добавляем продукты в приём пищи
                for food_name, grams in meal_plan:
                    if food_name in foods:
                        _, item_created = MealItem.objects.get_or_create(
                            meal=meal,
                            food_item=foods[food_name],
                            defaults={"grams": Decimal(str(grams))},
                        )
                        if item_created:
                            meal_items_created += 1

        if meals_created > 0:
            self.stdout.write(self.style.SUCCESS(f"  Создано приёмов пищи: {meals_created}"))
        if meal_items_created > 0:
            self.stdout.write(self.style.SUCCESS(f"  Создано позиций в приёмах: {meal_items_created}"))

        self.stdout.write(self.style.SUCCESS(f"\nГотово! Тестовые данные загружены для пользователя {user.username}"))

