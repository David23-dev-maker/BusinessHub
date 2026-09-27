from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.views import create_admin


urlpatterns = [

    path("admin/", admin.site.urls),
    path("", include("core.urls")),
    path("create-admin/", create_admin),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)