# Contenido para: frontend/frontend/urls.py

"""
URL configuration for frontend project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    # Esta línea le dice a Django que busque más URLs en 'web.urls'
    path("", include("web.urls")),
]
