from django.conf import settings
from django.db import models


class FoodItem(models.Model):
    class Source(models.TextChoices):
        MANUAL = "manual", "Вручную"
        OPENFOODFACTS = "openfoodfacts", "OpenFoodFacts"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Владелец продукта (null для продуктов из OpenFoodFacts - они глобальные)",
    )
    name = models.CharField(max_length=200)
    brand = models.CharField(max_length=200, blank=True)

    kcal_per_100g = models.DecimalField(max_digits=7, decimal_places=2)
    protein_per_100g = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    fat_per_100g = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    carb_per_100g = models.DecimalField(max_digits=7, decimal_places=2, default=0)

    source = models.CharField(max_length=32, choices=Source.choices, default=Source.MANUAL)
    external_id = models.CharField(max_length=128, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "external_id"],
                condition=~models.Q(external_id=""),
                name="uniq_fooditem_source_external_id",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class Meal(models.Model):
    class Type(models.TextChoices):
        BREAKFAST = "breakfast", "Завтрак"
        LUNCH = "lunch", "Обед"
        DINNER = "dinner", "Ужин"
        SNACK = "snack", "Перекус"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField()
    type = models.CharField(max_length=16, choices=Type.choices)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "type", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["user", "date", "type"], name="uniq_meal_per_day_type"),
        ]

    def __str__(self) -> str:
        return f"{self.user} — {self.date} — {self.get_type_display()}"


class MealItem(models.Model):
    meal = models.ForeignKey(Meal, on_delete=models.CASCADE, related_name="items")
    food_item = models.ForeignKey(FoodItem, on_delete=models.PROTECT)
    grams = models.DecimalField(max_digits=7, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.food_item} — {self.grams}г"

    def _scaled(self, per_100g: float) -> float:
        return (float(self.grams) / 100.0) * float(per_100g)

    @property
    def kcal(self) -> float:
        return self._scaled(self.food_item.kcal_per_100g)

    @property
    def protein(self) -> float:
        return self._scaled(self.food_item.protein_per_100g)

    @property
    def fat(self) -> float:
        return self._scaled(self.food_item.fat_per_100g)

    @property
    def carb(self) -> float:
        return self._scaled(self.food_item.carb_per_100g)


class Goal(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    start_date = models.DateField()
    target_date = models.DateField(null=True, blank=True)

    start_weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    target_weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    daily_kcal_target = models.PositiveIntegerField()
    daily_protein_target = models.PositiveIntegerField(null=True, blank=True)
    daily_fat_target = models.PositiveIntegerField(null=True, blank=True)
    daily_carb_target = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-is_active", "-start_date", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["user"], condition=models.Q(is_active=True), name="uniq_active_goal"),
        ]

    def __str__(self) -> str:
        return f"Цель {self.user} с {self.start_date} ({self.daily_kcal_target} ккал)"


class WeightLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField()
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["user", "date"], name="uniq_weightlog_per_day"),
        ]

    def __str__(self) -> str:
        return f"{self.user} — {self.date}: {self.weight_kg} кг"

# Create your models here.
