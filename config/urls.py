from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from store.tiles import tile
from django.conf import settings
from django.conf.urls.static import static
admin.site.site_header = "StepUp.in Administration"; admin.site.site_title = "StepUp.in"; admin.site.index_title = "Shop"; admin.site.index_template = "admin/stepup_index.html"; admin.site.site_url = settings.FRONTEND_URL
urlpatterns = [path("", RedirectView.as_view(url="/admin/")), path("tiles/<int:z>/<int:x>/<int:y>.png", tile), path("admin/", admin.site.urls), path("api/", include("store.urls"))] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
