from __future__ import annotations

import datetime as dt

from django import forms

from .models import FoodItem, Goal, Meal, MealItem, WeightLog


class FoodSearchForm(forms.Form):
    q = forms.CharField(
        label="Поиск продукта",
        max_length=120,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Например: yogurt"}),
    )


class AddMealItemForm(forms.Form):
    date = forms.DateField(
        label="Дата",
        initial=dt.date.today,
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
    )
    type = forms.ChoiceField(
        label="Приём пищи",
        choices=Meal.Type.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
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
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
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
            "start_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "target_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
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


