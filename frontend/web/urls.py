# Contenido para: frontend/web/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("operaciones/", views.operaciones, name="operaciones"),
    path(
        "operaciones/inicializar/",
        views.inicializar_sistema,
        name="inicializar_sistema",
    ),
    path("operaciones/consultar/", views.consultar_datos, name="consultar_datos"),
    path("operaciones/crear/", views.crear_datos, name="crear_datos"),
    path(
        "operaciones/facturacion/",
        views.proceso_facturacion,
        name="proceso_facturacion",
    ),
    path("operaciones/reportes/", views.reportes_pdf, name="reportes_pdf"),
]
