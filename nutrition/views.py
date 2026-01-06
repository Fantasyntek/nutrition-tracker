from __future__ import annotations

import datetime as dt

import pandas as pd
import plotly.graph_objects as go
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import F, FloatField, Sum
from django.db.models.functions import Cast
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import AddMealItemForm, FoodSearchForm, GoalForm, WeightLogForm
from .models import FoodItem, Goal, MealItem, WeightLog
from .services.openfoodfacts import OpenFoodFactsClient

# Create your views here.


def dashboard(request):
    if not request.user.is_authenticated:
        return render(request, "nutrition/landing.html")

    today = timezone.localdate()
    goal = Goal.objects.filter(user=request.user, is_active=True).first()

    # Агрегация последних 14 дней (ккал) для графика и таблички.
    start = today - dt.timedelta(days=13)
    qs = (
        MealItem.objects.filter(meal__user=request.user, meal__date__range=(start, today))
        .annotate(
            day=F("meal__date"),
            grams_f=Cast("grams", FloatField()),
            kcal100_f=Cast("food_item__kcal_per_100g", FloatField()),
        )
        .annotate(kcal=F("grams_f") * F("kcal100_f") / 100.0)
        .values("day")
        .annotate(kcal_sum=Sum("kcal"))
        .order_by("day")
    )
    df = pd.DataFrame(list(qs))
    if df.empty:
        df = pd.DataFrame({"day": [], "kcal_sum": []})

    # Заполняем пропуски дней нулями, чтобы график был ровным.
    all_days = pd.date_range(start=start, end=today, freq="D")
    df["day"] = pd.to_datetime(df["day"])
    df = df.set_index("day").reindex(all_days).fillna(0.0).rename_axis("day").reset_index()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["day"], y=df["kcal_sum"], mode="lines+markers", name="Ккал/день"))
    if goal:
        fig.add_hline(y=goal.daily_kcal_target, line_dash="dot", annotation_text="Цель", opacity=0.7)
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
    calories_chart_html = fig.to_html(full_html=False, include_plotlyjs="cdn")

    latest_weight = WeightLog.objects.filter(user=request.user).order_by("-date").first()

    context = {
        "today": today,
        "goal": goal,
        "latest_weight": latest_weight,
        "calories_chart_html": calories_chart_html,
    }
    return render(request, "nutrition/dashboard.html", context)


@login_required
def food_search(request):
    form = FoodSearchForm(request.GET or None)
    results = []
    if form.is_valid():
        client = OpenFoodFactsClient()
        try:
            results = client.search(form.cleaned_data["q"], limit=10)
        except Exception:
            messages.error(request, "Не удалось получить данные из OpenFoodFacts. Попробуйте позже.")

    return render(
        request,
        "nutrition/food_search.html",
        {
            "form": form,
            "results": results,
        },
    )


@login_required
def food_import(request):
    if request.method != "POST":
        return redirect("nutrition:food_search")

    code = (request.POST.get("code") or "").strip()
    if not code:
        messages.error(request, "Не передан код продукта.")
        return redirect("nutrition:food_search")

    client = OpenFoodFactsClient()
    try:
        p = client.get_product(code)
    except Exception:
        p = None

    if not p or p.kcal_100g is None:
        messages.error(request, "Не удалось импортировать продукт: нет данных по калорийности (на 100г).")
        return redirect("nutrition:food_search")

    obj, created = FoodItem.objects.update_or_create(
        source=FoodItem.Source.OPENFOODFACTS,
        external_id=p.code,
        defaults={
            "name": p.name[:200],
            "brand": p.brand[:200],
            "kcal_per_100g": round(p.kcal_100g or 0, 2),
            "protein_per_100g": round(p.protein_100g or 0, 2),
            "fat_per_100g": round(p.fat_100g or 0, 2),
            "carb_per_100g": round(p.carbs_100g or 0, 2),
        },
    )

    messages.success(request, f"Продукт {'добавлен' if created else 'обновлён'}: {obj.name}")
    return redirect("nutrition:food_search")


@login_required
def add_meal_item(request):
    if request.method == "POST":
        form = AddMealItemForm(request.POST)
        if form.is_valid():
            form.save(user=request.user)
            messages.success(request, "Запись добавлена в дневник.")
            return redirect("nutrition:dashboard")
    else:
        form = AddMealItemForm()

    return render(request, "nutrition/add_meal_item.html", {"form": form})


@login_required
def add_weight(request):
    if request.method == "POST":
        form = WeightLogForm(request.POST)
        if form.is_valid():
            form.save(user=request.user)
            messages.success(request, "Вес сохранён.")
            return redirect("nutrition:dashboard")
    else:
        form = WeightLogForm(initial={"date": timezone.localdate()})

    return render(request, "nutrition/add_weight.html", {"form": form})


@login_required
def set_goal(request):
    goal = Goal.objects.filter(user=request.user, is_active=True).first()
    if request.method == "POST":
        form = GoalForm(request.POST, instance=goal)
        if form.is_valid():
            form.save(user=request.user)
            messages.success(request, "Цель сохранена.")
            return redirect("nutrition:dashboard")
    else:
        form = GoalForm(instance=goal, initial={"start_date": timezone.localdate()})

    return render(request, "nutrition/set_goal.html", {"form": form})