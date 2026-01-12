from django.urls import path

from . import views


app_name = "nutrition"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("register/", views.register, name="register"),
    path("foods/search/", views.food_search, name="food_search"),
    path("foods/import/", views.food_import, name="food_import"),
    path("foods/add-manual/", views.add_food_manual, name="add_food_manual"),
    path("meals/add-item/", views.add_meal_item, name="add_meal_item"),
    path("weight/add/", views.add_weight, name="add_weight"),
    path("goal/set/", views.set_goal, name="set_goal"),
]


