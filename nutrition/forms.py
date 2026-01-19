from __future__ import annotations

import datetime as dt

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone

from .models import FoodItem, Goal, Meal, MealItem, WeightLog

User = get_user_model()

EN_MEAL_TYPE_LABELS = {
    Meal.Type.BREAKFAST: "Breakfast",
    Meal.Type.LUNCH: "Lunch",
    Meal.Type.DINNER: "Dinner",
    Meal.Type.SNACK: "Snack",
}


def _t(lang: str | None, ru: str, en: str) -> str:
    return en if lang == "en" else ru


class CustomDateInput(forms.DateInput):
    """Кастомный виджет для выбора даты с flatpickr."""

    def __init__(self, attrs=None):
        default_attrs = {"class": "input custom-date", "placeholder": "дд.мм.гггг"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs, format="%Y-%m-%d")


class CustomSelect(forms.Select):
    """Кастомный виджет для выбора с Choices.js стилями."""

    def __init__(self, attrs=None):
        default_attrs = {"class": "select custom-select"}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)


class UserRegistrationForm(UserCreationForm):
    """Форма регистрации пользователя."""

    email = forms.EmailField(
        label="Email",
        required=True,
        widget=forms.EmailInput(attrs={"class": "input"}),
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
        widgets = {
            "username": forms.TextInput(attrs={"class": "input"}),
        }

    def __init__(self, *args, **kwargs):
        lang = kwargs.pop("lang", None)
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs.update({"class": "input"})
        self.fields["password2"].widget.attrs.update({"class": "input"})

        # Optional localization for labels (templates also override some labels)
        self.fields["username"].label = _t(lang, "Логин", "Username")
        self.fields["email"].label = "Email"
        self.fields["password1"].label = _t(lang, "Пароль", "Password")
        self.fields["password2"].label = _t(lang, "Повторите пароль", "Confirm password")


class FoodSearchForm(forms.Form):
    q = forms.CharField(max_length=120, required=True, widget=forms.TextInput(attrs={"class": "input"}))

    def __init__(self, *args, **kwargs):
        lang = kwargs.pop("lang", None)
        super().__init__(*args, **kwargs)
        self.fields["q"].label = _t(lang, "Поиск продукта", "Search food")
        self.fields["q"].widget.attrs.update(
            {"placeholder": _t(lang, "Например: йогурт, хлеб, курица", "E.g. yogurt, bread, chicken")}
        )


class ManualFoodItemForm(forms.ModelForm):
    """Форма для ручного добавления продукта."""

    class Meta:
        model = FoodItem
        fields = ["name", "brand", "kcal_per_100g", "protein_per_100g", "fat_per_100g", "carb_per_100g"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input", "placeholder": "Название продукта"}),
            "brand": forms.TextInput(attrs={"class": "input", "placeholder": "Бренд (необязательно)"}),
            "kcal_per_100g": forms.NumberInput(attrs={"class": "input", "step": "0.01", "min": "0"}),
            "protein_per_100g": forms.NumberInput(attrs={"class": "input", "step": "0.01", "min": "0"}),
            "fat_per_100g": forms.NumberInput(attrs={"class": "input", "step": "0.01", "min": "0"}),
            "carb_per_100g": forms.NumberInput(attrs={"class": "input", "step": "0.01", "min": "0"}),
        }
        labels = {
            "name": "Название",
            "brand": "Бренд",
            "kcal_per_100g": "Калории (на 100г)",
            "protein_per_100g": "Белки (на 100г, г)",
            "fat_per_100g": "Жиры (на 100г, г)",
            "carb_per_100g": "Углеводы (на 100г, г)",
        }

    def __init__(self, *args, **kwargs):
        lang = kwargs.pop("lang", None)
        super().__init__(*args, **kwargs)
        self.fields["name"].label = _t(lang, "Название", "Name")
        self.fields["brand"].label = _t(lang, "Бренд", "Brand")
        self.fields["kcal_per_100g"].label = _t(lang, "Калории (на 100г)", "Calories (per 100g)")
        self.fields["protein_per_100g"].label = _t(lang, "Белки (на 100г, г)", "Protein (per 100g, g)")
        self.fields["fat_per_100g"].label = _t(lang, "Жиры (на 100г, г)", "Fat (per 100g, g)")
        self.fields["carb_per_100g"].label = _t(lang, "Углеводы (на 100г, г)", "Carbs (per 100g, g)")
        # Placeholders
        self.fields["name"].widget.attrs.update({"placeholder": _t(lang, "Название продукта", "Food name")})
        self.fields["brand"].widget.attrs.update({"placeholder": _t(lang, "Бренд (необязательно)", "Brand (optional)")})


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
        queryset=FoodItem.objects.none(),  # Будет установлен в __init__
        widget=CustomSelect(),
    )
    grams = forms.DecimalField(
        label="Граммы",
        min_value=1,
        decimal_places=2,
        max_digits=7,
        widget=forms.NumberInput(attrs={"class": "input", "step": "0.01"}),
    )

    def __init__(self, *args, **kwargs):
        lang = kwargs.pop("lang", None)
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["date"].label = _t(lang, "Дата", "Date")
        self.fields["type"].label = _t(lang, "Приём пищи", "Meal")
        self.fields["food_item"].label = _t(lang, "Продукт", "Food")
        self.fields["grams"].label = _t(lang, "Граммы", "Grams")
        if lang == "en":
            self.fields["type"].choices = [(v, EN_MEAL_TYPE_LABELS.get(v, label)) for v, label in Meal.Type.choices]
        # Фильтруем продукты: показываем глобальные (OpenFoodFacts) и продукты текущего пользователя
        if user:
            from django.db.models import Q
            self.fields["food_item"].queryset = FoodItem.objects.filter(Q(user=user) | Q(user__isnull=True))

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
            "weight_kg": forms.NumberInput(attrs={"class": "input", "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        lang = kwargs.pop("lang", None)
        super().__init__(*args, **kwargs)
        self._lang = lang
        self.fields["date"].label = _t(lang, "Дата", "Date")
        self.fields["weight_kg"].label = _t(lang, "Вес (кг)", "Weight (kg)")

    def clean_date(self):
        d = self.cleaned_data.get("date")
        if d and d > timezone.localdate():
            raise forms.ValidationError(
                _t(self._lang, "Нельзя указать будущую дату.", "You can't set a future date.")
            )
        return d

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
            "start_weight_kg": forms.NumberInput(attrs={"class": "input", "step": "0.01"}),
            "target_weight_kg": forms.NumberInput(attrs={"class": "input", "step": "0.01"}),
            "daily_kcal_target": forms.NumberInput(attrs={"class": "input", "min": 1}),
            "daily_protein_target": forms.NumberInput(attrs={"class": "input", "min": 0}),
            "daily_fat_target": forms.NumberInput(attrs={"class": "input", "min": 0}),
            "daily_carb_target": forms.NumberInput(attrs={"class": "input", "min": 0}),
        }

    def save(self, commit=True, *, user):
        Goal.objects.filter(user=user, is_active=True).update(is_active=False)
        obj = super().save(commit=False)
        obj.user = user
        obj.is_active = True
        if commit:
            obj.save()
        return obj


