from django.urls import path
from . import views


urlpatterns = [
    path("list-business/", views.list_business, name="list_business"),
    path("business-success/", views.business_success, name="business_success"),
    path("businesses/", views.business_list, name="business_list"),
    path("owner-dashboard/", views.owner_dashboard, name="owner_dashboard"),

    path("view-business/<int:business_id>/", views.view_business, name="view_business"),
    path("edit-business/<int:business_id>/", views.edit_business, name="edit_business"),
    path("delete-business/<int:business_id>/", views.delete_business, name="delete_business"),

    path("login/", views.user_login, name="login"),
    path("", views.home, name="home"),
    path("categories/", views.categories, name="categories"),
    path("tracking/", views.tracking, name="tracking"),
    path(
    "api/package-location/<str:tracking_number>/",
    views.package_location_api,
    name="package_location_api"
),
path(
    "api/save-package-location/<str:tracking_number>/",
    views.save_package_location_api,
    name="save_package_location_api"
),
]