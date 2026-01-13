from __future__ import annotations

import datetime as dt

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import FoodItem, Goal, Meal, MealItem, WeightLog

User = get_user_model()


class CustomDateInput(forms.DateInput):
    """Кастомный виджет для выбора даты с flatpickr."""

    def __init__(self, attrs=None):
        default_attrs = {"class": "form-control custom-date", "placeholder": "дд.мм.гггг"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs, format="%Y-%m-%d")


class CustomSelect(forms.Select):
    """Кастомный виджет для выбора с Choices.js стилями."""

    def __init__(self, attrs=None):
        default_attrs = {"class": "form-select custom-select"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)


class UserRegistrationForm(UserCreationForm):
    """Форма регистрации пользователя."""

    email = forms.EmailField(
        label="Email",
        required=True,
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs.update({"class": "form-control"})
        self.fields["password2"].widget.attrs.update({"class": "form-control"})


class FoodSearchForm(forms.Form):
    q = forms.CharField(
        label="Поиск продукта",
        max_length=120,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Например: йогурт, хлеб, курица"}),
    )


class ManualFoodItemForm(forms.ModelForm):
    """Форма для ручного добавления продукта."""

    class Meta:
        model = FoodItem
        fields = ["name", "brand", "kcal_per_100g", "protein_per_100g", "fat_per_100g", "carb_per_100g"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Название продукта"}),
            "brand": forms.TextInput(attrs={"class": "form-control", "placeholder": "Бренд (необязательно)"}),
            "kcal_per_100g": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "protein_per_100g": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "fat_per_100g": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
            "carb_per_100g": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0"}),
        }
        labels = {
            "name": "Название",
            "brand": "Бренд",
            "kcal_per_100g": "Калории (на 100г)",
            "protein_per_100g": "Белки (на 100г, г)",
            "fat_per_100g": "Жиры (на 100г, г)",
            "carb_per_100g": "Углеводы (на 100г, г)",
        }


class AddMealItemForm(forms.Form):
    date = forms.DateField(
        label="Дата",
        initial=dt.date.today,
        widget=CustomDateInput(),
    )
    type = forms.ChoiceField(
        label="Приём пищи",
        choices=Meal.Type.choices,
        widget=CustomSelect(),
    )
    food_item = forms.ModelChoiceField(
        label="Продукт",
        queryset=FoodItem.objects.all(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    grams = forms.DecimalField(
        label="Граммы",
        min_value=1,
        decimal_places=2,
        max_digits=7,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
    )

    def save(self, *, user) -> MealItem:
        meal, _ = Meal.objects.get_or_create(user=user, date=self.cleaned_data["date"], type=self.cleaned_data["type"])
        return MealItem.objects.create(
            meal=meal,
            food_item=self.cleaned_data["food_item"],
            grams=self.cleaned_data["grams"],
        )


class WeightLogForm(forms.ModelForm):
    class Meta:
        model = WeightLog
        fields = ["date", "weight_kg"]
        widgets = {
            "date": CustomDateInput(),
            "weight_kg": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }

    def save(self, commit=True, *, user):
        obj = super().save(commit=False)
        obj.user = user
        if commit:
            obj.save()
        return obj


class GoalForm(forms.ModelForm):
    class Meta:
        model = Goal
        fields = [
            "start_date",
            "target_date",
            "start_weight_kg",
            "target_weight_kg",
            "daily_kcal_target",
            "daily_protein_target",
            "daily_fat_target",
            "daily_carb_target",
        ]
        widgets = {
            "start_date": CustomDateInput(),
            "target_date": CustomDateInput(),
            "start_weight_kg": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "target_weight_kg": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "daily_kcal_target": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "daily_protein_target": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "daily_fat_target": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "daily_carb_target": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
        }

    def save(self, commit=True, *, user):
        Goal.objects.filter(user=user, is_active=True).update(is_active=False)
        obj = super().save(commit=False)
        obj.user = user
        obj.is_active = True
        if commit:
            obj.save()
        return obj


