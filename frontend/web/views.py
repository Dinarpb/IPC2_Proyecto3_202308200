# Contenido para: frontend/web/views.py

from django.shortcuts import render, redirect
from django.http import JsonResponse
import requests

API_URL = "http://localhost:3000/"


def index(request):
    message = None
    if request.method == "POST":
        file = None
        endpoint = None
        message_type = None

        if "configuracion_file" in request.FILES:
            file = request.FILES["configuracion_file"]
            endpoint = "configuracion"
            message_type = "configuracion"

        elif "consumo_file" in request.FILES:
            file = request.FILES["consumo_file"]
            endpoint = "consumo" 
            message_type = "consumo"

        if file and endpoint:
            files = {"file": (file.name, file.read(), file.content_type)}
            try:
                response = requests.post(API_URL + endpoint, files=files)

                if response.status_code == 200:
                    data = response.json()

                    if message_type == "configuracion":
                        message = (
                            f"{data.get('nuevos_clientes', 0)} nuevos clientes creados, "
                            f"{data.get('nuevas_instancias', 0)} nuevas instancias creadas, "
                            f"{data.get('nuevos_recursos', 0)} nuevos recursos creados, "
                            f"{data.get('nuevas_categorias', 0)} nueva(s) categoría(s) creada(s)"
                        )
                    elif message_type == "consumo":
                        message = f"{data.get('nuevos_consumos', 0)} nuevos consumos procesados."

                else:
                    message = (
                        f"Error del backend: {response.status_code} - {response.text}"
                    )

            except requests.exceptions.RequestException as e:
                message = f"Error de conexión con el API: {e}"

        elif not message:
            message = "No se seleccionó un archivo válido."

    return render(request, "index.html", {"message": message})
