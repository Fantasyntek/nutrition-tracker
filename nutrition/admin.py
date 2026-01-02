from django.contrib import admin

from .models import FoodItem, Goal, Meal, MealItem, WeightLog


@admin.register(FoodItem)
class FoodItemAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "brand", "kcal_per_100g", "source", "created_at")
    list_filter = ("source",)
    search_fields = ("name", "brand", "external_id")


class MealItemInline(admin.TabularInline):
    model = MealItem
    extra = 0
    autocomplete_fields = ("food_item",)


@admin.register(Meal)
class MealAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "date", "type", "created_at")
    list_filter = ("type", "date")
    search_fields = ("user__username", "user__email")
    date_hierarchy = "date"
    inlines = [MealItemInline]


@admin.register(Goal)
class GoalAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "start_date", "daily_kcal_target", "is_active", "created_at")
    list_filter = ("is_active", "start_date")
    search_fields = ("user__username", "user__email")


@admin.register(WeightLog)
class WeightLogAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "date", "weight_kg", "created_at")
    list_filter = ("date",)
    search_fields = ("user__username", "user__email")
    date_hierarchy = "date"

# Register your models here.
