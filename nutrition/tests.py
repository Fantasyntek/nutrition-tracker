from __future__ import annotations

from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import FoodItem, Goal, Meal, MealItem
from .services.openfoodfacts import OpenFoodFactsClient

User = get_user_model()


class ThemeCookieTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u1", password="pass12345")
        self.client = Client()
        self.client.force_login(self.user)

    def test_toggle_theme_sets_cookie_and_logout_preserves(self):
        # Toggle -> should set cookie
        r1 = self.client.post(reverse("toggle_theme"), {"next": "/"})
        self.assertEqual(r1.status_code, 302)
        self.assertIn("theme", r1.cookies)
        theme_cookie = r1.cookies["theme"].value
        self.assertIn(theme_cookie, ("light", "dark"))

        # Logout -> should keep cookie value
        r2 = self.client.post(reverse("logout"))
        self.assertEqual(r2.status_code, 302)
        self.assertIn("theme", r2.cookies)
        self.assertEqual(r2.cookies["theme"].value, theme_cookie)


class DashboardProgressTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u2", password="pass12345")
        self.client = Client()
        self.client.force_login(self.user)

    def test_progress_calculated_from_goal(self):
        today = timezone.localdate()
        Goal.objects.create(user=self.user, start_date=today, daily_kcal_target=2000, is_active=True)
        food = FoodItem.objects.create(
            name="Test food",
            brand="",
            kcal_per_100g=100,
            protein_per_100g=10,
            fat_per_100g=5,
            carb_per_100g=20,
            source=FoodItem.Source.MANUAL,
        )
        meal = Meal.objects.create(user=self.user, date=today, type=Meal.Type.BREAKFAST)
        MealItem.objects.create(meal=meal, food_item=food, grams=50)  # 50 kcal

        r = self.client.get(reverse("nutrition:dashboard"))
        self.assertEqual(r.status_code, 200)
        progress = r.context["progress"]
        self.assertEqual(progress["kcal"], 2)  # 50/2000=2.5% -> int() => 2


class I18nFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u3", password="pass12345")
        self.client = Client()
        self.client.force_login(self.user)

    def test_add_food_page_uses_english_choices_when_lang_en(self):
        # Set session language to en
        session = self.client.session
        session["django_language"] = "en"
        session.save()

        r = self.client.get(reverse("nutrition:add_meal_item"))
        self.assertEqual(r.status_code, 200)
        body = r.content.decode("utf-8")
        # One of meal types should be in English
        self.assertIn("Breakfast", body)


class OpenFoodFactsClientTests(TestCase):
    def test_search_uses_fields_and_fallback(self):
        client = OpenFoodFactsClient()

        def mk_response(payload):
            resp = Mock()
            resp.raise_for_status = Mock()
            resp.json = Mock(return_value=payload)
            return resp

        with patch("nutrition.services.openfoodfacts.requests.get") as mget:
            mget.side_effect = [
                mk_response({"products": []}),  # first attempt (russia) empty -> fallback
                mk_response({"products": [{"code": "1", "product_name": "X", "brands": "B", "nutriments": {}}]}),
            ]
            res = client.search("test", limit=1)
            self.assertEqual(len(res), 1)

            # Verify fields param used at least once
            called_params = mget.call_args_list[0].kwargs.get("params") or {}
            self.assertIn("fields", called_params)
            self.assertIn("nutriments", called_params["fields"])
