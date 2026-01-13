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
from django.views.decorators.http import require_http_methods

from .forms import AddMealItemForm, FoodSearchForm, GoalForm, ManualFoodItemForm, UserRegistrationForm, WeightLogForm
from .models import FoodItem, Goal, MealItem, WeightLog
from .services.openfoodfacts import OpenFoodFactsClient

# Create your views here.


def dashboard(request):
    if not request.user.is_authenticated:
        return render(request, "nutrition/landing.html")

    today = timezone.localdate()
    goal = Goal.objects.filter(user=request.user, is_active=True).first()

    # Агрегация последних 14 дней (КБЖУ) для графика и таблички.
    start = today - dt.timedelta(days=13)
    qs = (
        MealItem.objects.filter(meal__user=request.user, meal__date__range=(start, today))
        .annotate(
            day=F("meal__date"),
            grams_f=Cast("grams", FloatField()),
            kcal100_f=Cast("food_item__kcal_per_100g", FloatField()),
            protein100_f=Cast("food_item__protein_per_100g", FloatField()),
            fat100_f=Cast("food_item__fat_per_100g", FloatField()),
            carb100_f=Cast("food_item__carb_per_100g", FloatField()),
        )
        .annotate(
            kcal=F("grams_f") * F("kcal100_f") / 100.0,
            protein=F("grams_f") * F("protein100_f") / 100.0,
            fat=F("grams_f") * F("fat100_f") / 100.0,
            carb=F("grams_f") * F("carb100_f") / 100.0,
        )
        .values("day")
        .annotate(
            kcal_sum=Sum("kcal"),
            protein_sum=Sum("protein"),
            fat_sum=Sum("fat"),
            carb_sum=Sum("carb"),
        )
        .order_by("day")
    )
    df = pd.DataFrame(list(qs))
    if df.empty:
        df = pd.DataFrame({"day": [], "kcal_sum": [], "protein_sum": [], "fat_sum": [], "carb_sum": []})

    # Заполняем пропуски дней нулями, чтобы график был ровным.
    all_days = pd.date_range(start=start, end=today, freq="D")
    df["day"] = pd.to_datetime(df["day"])
    df = df.set_index("day").reindex(all_days).fillna(0.0).rename_axis("day").reset_index()

    # График калорий
    fig_cal = go.Figure()
    fig_cal.add_trace(go.Scatter(x=df["day"], y=df["kcal_sum"], mode="lines+markers", name="Ккал/день"))
    if goal:
        fig_cal.add_hline(y=goal.daily_kcal_target, line_dash="dot", annotation_text="Цель", opacity=0.7)
    fig_cal.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10), title="Калории за 14 дней")
    calories_chart_html = fig_cal.to_html(full_html=False, include_plotlyjs="cdn")

    # Статистика за сегодня
    today_stats = df[df["day"].dt.date == today]
    today_kcal = float(today_stats["kcal_sum"].iloc[0]) if not today_stats.empty else 0.0
    today_protein = float(today_stats["protein_sum"].iloc[0]) if not today_stats.empty else 0.0
    today_fat = float(today_stats["fat_sum"].iloc[0]) if not today_stats.empty else 0.0
    today_carb = float(today_stats["carb_sum"].iloc[0]) if not today_stats.empty else 0.0

    # График веса (последние 30 дней)
    weight_start = today - dt.timedelta(days=29)
    weight_logs = WeightLog.objects.filter(user=request.user, date__range=(weight_start, today)).order_by("date")
    weight_chart_html = None
    if weight_logs.exists():
        weight_df = pd.DataFrame([{"date": w.date, "weight": float(w.weight_kg)} for w in weight_logs])
        weight_df["date"] = pd.to_datetime(weight_df["date"])
        weight_df = weight_df.sort_values("date")

        fig_weight = go.Figure()
        fig_weight.add_trace(go.Scatter(x=weight_df["date"], y=weight_df["weight"], mode="lines+markers", name="Вес (кг)"))
        if goal and goal.target_weight_kg:
            fig_weight.add_hline(y=float(goal.target_weight_kg), line_dash="dot", annotation_text="Цель", opacity=0.7)
        fig_weight.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10), title="Динамика веса")
        weight_chart_html = fig_weight.to_html(full_html=False, include_plotlyjs="cdn")

    latest_weight = WeightLog.objects.filter(user=request.user).order_by("-date").first()

    # Прогноз веса на основе дефицита/профицита калорий
    # Формула: 7700 ккал ≈ 1 кг веса
    weight_forecast = None
    if goal and goal.start_weight_kg and latest_weight:
        # Считаем накопленный дефицит/профицит с начала цели
        goal_start = max(goal.start_date, start)
        deficit_qs = (
            MealItem.objects.filter(meal__user=request.user, meal__date__gte=goal_start, meal__date__lte=today)
            .annotate(
                grams_f=Cast("grams", FloatField()),
                kcal100_f=Cast("food_item__kcal_per_100g", FloatField()),
            )
            .annotate(kcal=F("grams_f") * F("kcal100_f") / 100.0)
            .aggregate(total_kcal=Sum("kcal"))
        )
        total_kcal = float(deficit_qs["total_kcal"] or 0)
        days_count = (today - goal_start).days + 1
        expected_kcal = float(goal.daily_kcal_target) * days_count
        deficit_kcal = expected_kcal - total_kcal
        # 7700 ккал ≈ 1 кг
        weight_change_kg = deficit_kcal / 7700.0
        predicted_weight = float(goal.start_weight_kg) - weight_change_kg
        weight_forecast = {
            "predicted_weight": round(predicted_weight, 2),
            "weight_change": round(weight_change_kg, 2),
            "deficit_kcal": round(deficit_kcal, 0),
        }

    context = {
        "today": today,
        "goal": goal,
        "latest_weight": latest_weight,
        "calories_chart_html": calories_chart_html,
        "weight_chart_html": weight_chart_html,
        "weight_forecast": weight_forecast,
        "today_kcal": round(today_kcal, 0),
        "today_protein": round(today_protein, 1),
        "today_fat": round(today_fat, 1),
        "today_carb": round(today_carb, 1),
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


def register(request):
    """Регистрация нового пользователя."""
    if request.user.is_authenticated:
        return redirect("nutrition:dashboard")

    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Регистрация успешна! Добро пожаловать, {user.username}.")
            from django.contrib.auth import login

            login(request, user)
            return redirect("nutrition:dashboard")
    else:
        form = UserRegistrationForm()

    return render(request, "registration/register.html", {"form": form})


@login_required
def add_food_manual(request):
    """Ручное добавление продукта в базу."""
    if request.method == "POST":
        form = ManualFoodItemForm(request.POST)
        if form.is_valid():
            food = form.save(commit=False)
            food.source = FoodItem.Source.MANUAL
            food.save()
            messages.success(request, f"Продукт '{food.name}' добавлен в базу.")
            return redirect("nutrition:food_search")
    else:
        form = ManualFoodItemForm()

    return render(request, "nutrition/add_food_manual.html", {"form": form})


@require_http_methods(["POST"])
def set_language(request):
    """Простое переключение языка через сессию."""
    lang = request.POST.get("language", "ru")
    if lang in ["ru", "en"]:
        request.session["django_language"] = lang
    return redirect(request.POST.get("next", "/"))
