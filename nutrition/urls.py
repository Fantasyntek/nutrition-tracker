from django.urls import path

from . import views


app_name = "nutrition"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("foods/search/", views.food_search, name="food_search"),
    path("foods/import/", views.food_import, name="food_import"),
    path("meals/add-item/", views.add_meal_item, name="add_meal_item"),
    path("weight/add/", views.add_weight, name="add_weight"),
    path("goal/set/", views.set_goal, name="set_goal"),
]


