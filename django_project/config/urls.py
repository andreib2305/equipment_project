from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    # Кнопка «Открыть сайт» в админке ведёт на "/", а не в 404.
    path(
        "",
        RedirectView.as_view(url="/api/", permanent=False),
        name="home",
    ),
    path("admin/", admin.site.urls),
    path("api/", include("maintenance.urls")),
]
